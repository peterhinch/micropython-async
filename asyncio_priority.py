# asyncio_priority.py Modified version of uasyncio with priority mechanism.

# Updated 18th Dec 2017 for uasyncio.core V1.6
# New low priority algorithm reduces differences in run_forever compared to
# standard uasyncio.

# The MIT License (MIT)
#
# Copyright (c) 2017 Peter Hinch
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import utime as time
import utimeq
from uasyncio import *

class PriorityEventLoop(PollEventLoop):
    def __init__(self, len=42, lpqlen=42):
        super().__init__(len)
        self._max_overdue_ms = 0
        self.lpq = utimeq.utimeq(lpqlen)
        self.hp_tasks = None
        self.create_task(self.lp_monitor())

    # Monitor low priority tasks. If one can be scheduled, remove from LP queue
    # and queue it for scheduling.
    # If a normal task is ready we only queue an LP one which is due by more
    # than the max_overdue_ms threshold.
    # If no normal task is ready we queue the most overdue LP task.
    # Readiness is determined by whether it is actually due. An option would be
    # to check if it's due in less than N ms. This would reduce competition at
    # the cost of the application having to consider tight loops which pend for
    # < N ms.
    async def lp_monitor(self):
        this_task = [0, 0, 0]
        while True:
            if self.lpq:
                tnow = self.time()
                t = self.lpq.peektime()
                tim = time.ticks_diff(t, tnow)
                to_run = self._max_overdue_ms > 0 and tim < -self._max_overdue_ms
                if not to_run:  # No overdue LP task. Are any normal tasks due?
                    can_run = True  # If q is empty can run an LP task
                    if self.q:
                        t = self.q.peektime()
                        can_run = time.ticks_diff(t, tnow) > 0 # No normal task is ready -
                    to_run = can_run and tim <= 0  # run if so and an LP one is ready
                if to_run:
                    self.lpq.pop(this_task)
                    self.q.push(*this_task)
            yield

    def max_overdue_ms(self, t=None):
        if t is not None:
            self._max_overdue_ms = t
        return self._max_overdue_ms

    # Low priority versions of call_later() call_later_ms() and call_at_()
    def call_after_ms(self, delay, callback, *args):
        self.call_at_lp_(time.ticks_add(self.time(), delay), callback, args)

    def call_after(self, delay, callback, *args):
        self.call_at_lp_(time.ticks_add(self.time(), int(delay * 1000)), callback, args)

    def call_at_lp_(self, time, callback, args=()):
        self.lpq.push(time, callback, args)

    def _schedule_hp(self, func, callback, args=()):
        if self.hp_tasks is None:
            self.hp_tasks = []
        # If there's an empty slot, assign without allocation
        for entry in self.hp_tasks:  # O(N) search - but N is typically 1 or 2...
            if not entry[0]:
                entry[0] = func
                entry[1] = callback
                entry[2] = args
                break
        else:
            self.hp_tasks.append([func, callback, args])

    def run_forever(self):
        cur_task = [0, 0, 0]
        while True:
            if self.q:
                # wait() may finish prematurely due to I/O completion,
                # and schedule new, earlier than before tasks to run.
                while 1:
                    # Check list of high priority tasks
                    if self.hp_tasks is not None:
                        hp_found = False
                        for entry in self.hp_tasks:
                            if entry[0] and entry[0]():
                                hp_found = True
                                entry[0] = 0
                                cur_task[0] = 0
                                cur_task[1] = entry[1] # ??? quick non-allocating copy
                                cur_task[2] = entry[2]
                                break
                        if hp_found:
                            break

                    # Schedule any due normal task
                    t = self.q.peektime()
                    tnow = self.time()
                    delay = time.ticks_diff(t, tnow)
                    if delay <= 0:
                        # Always call wait(), to give a chance to I/O scheduling
                        self.wait(0)
                        self.q.pop(cur_task)
                        break

                    self.wait(delay)  # Handled in superclass
                t = cur_task[0]
                cb = cur_task[1]
                args = cur_task[2]
                if __debug__ and DEBUG:
                    log.debug("Next coroutine to run: %s", (t, cb, args))
#                __main__.mem_info()
                self.cur_task = cb
            else:
                self.wait(-1)
                # Assuming IO completion scheduled some tasks
                continue
            if callable(cb):
                cb(*args)
            else:
                delay = 0
                func = None
                priority = True
                try:
                    if __debug__ and DEBUG:
                        log.debug("Coroutine %s send args: %s", cb, args)
                    if args == ():
                        ret = next(cb)  # See notes at end of code
                    else:
                        ret = cb.send(*args)
                    if __debug__ and DEBUG:
                        log.debug("Coroutine %s yield result: %s", cb, ret)
                    if isinstance(ret, SysCall1):
                        arg = ret.arg
                        if isinstance(ret, After):
                            delay = int(arg * 1000)
                            priority = False
                        elif isinstance(ret, AfterMs):
                            delay = int(arg)
                            priority = False
                        elif isinstance(ret, When):
                            if callable(arg):
                                func = arg
                            else:
                                assert False, "Argument to 'when' must be a function or method."
                        elif isinstance(ret, SleepMs):
                            delay = arg
                        elif isinstance(ret, IORead):
                            self.add_reader(arg, cb)
                            continue
                        elif isinstance(ret, IOWrite):
                            self.add_writer(arg, cb)
                            continue
                        elif isinstance(ret, IOReadDone):
                            self.remove_reader(arg)
                        elif isinstance(ret, IOWriteDone):
                            self.remove_writer(arg)
                        elif isinstance(ret, StopLoop):
                            return arg
                        else:
                            assert False, "Unknown syscall yielded: %r (of type %r)" % (ret, type(ret))
                    elif isinstance(ret, type_gen):
                        self.call_soon(ret)
                    elif isinstance(ret, int):
                        # Delay
                        delay = ret
                    elif ret is None:
                        # Just reschedule
                        pass
                    elif ret is False:
                        # Don't reschedule
                        continue
                    else:
                        assert False, "Unsupported coroutine yield value: %r (of type %r)" % (ret, type(ret))
                except StopIteration as e:
                    if __debug__ and DEBUG:
                        log.debug("Coroutine finished: %s", cb)
                    continue

                if func is not None:
                    self._schedule_hp(func, cb)
                else:
                    # Currently all syscalls don't return anything, so we don't
                    # need to feed anything to the next invocation of coroutine.
                    # If that changes, need to pass that value below.
                    if priority:
                        self.call_later_ms(delay, cb)
                    else:
                        self.call_after_ms(delay, cb)


# Low priority
class AfterMs(SleepMs):
    pass

class After(AfterMs):
    pass

# High Priority
class When(SleepMs):
    pass

after_ms = AfterMs()
after = After()
when = When()

import uasyncio.core
uasyncio.core._event_loop_class = PriorityEventLoop
def get_event_loop(len=42, lpqlen=42):
    if uasyncio.core._event_loop is None:  # Add a q entry for lp_monitor()
        uasyncio.core._event_loop = uasyncio.core._event_loop_class(len + 1, lpqlen)
    return uasyncio.core._event_loop
