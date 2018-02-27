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
import ucollections
from uasyncio import *

class PriorityEventLoop(PollEventLoop):
    def __init__(self, runq_len=16, waitq_len=16, lpqlen=42):
        super().__init__(runq_len, waitq_len)
        self._max_overdue_ms = 0
        self.lpq = utimeq.utimeq(lpqlen)
        self.hp_tasks = []

    # Schedule a single low priority task if one is ready or overdue.
    # The most overdue task is scheduled even if normal tasks are pending.
    # The most due task is scheduled only if no normal tasks are pending.
    def schedule_lp_task(self, cur_task, tnow):
        t = self.lpq.peektime()
        tim = time.ticks_diff(t, tnow)
        to_run = self._max_overdue_ms > 0 and tim < -self._max_overdue_ms
        if not to_run:  # No overdue LP task.
            if len(self.runq):  # zero delay tasks go straight to runq
                return False
            to_run = tim <= 0  # True if LP task is due
            if to_run and self.waitq:  # Set False if a normal tasks is due.
                t = self.waitq.peektime()
                to_run = time.ticks_diff(t, tnow) > 0 # No normal task is ready
        if to_run:
            self.lpq.pop(cur_task)
            self.call_soon(cur_task[1], *cur_task[2])
            return True
        return False

    def max_overdue_ms(self, t=None):
        if t is not None:
            self._max_overdue_ms = t
        return self._max_overdue_ms

    # Low priority versions of call_later() call_later_ms() and call_at_()
    def call_after_ms(self, delay, callback, *args):
        self.call_at_lp_(time.ticks_add(self.time(), delay), callback, *args)


    def call_after(self, delay, callback, *args):
        self.call_at_lp_(time.ticks_add(self.time(), int(delay * 1000)), callback, *args)

    def call_at_lp_(self, time, callback, *args):
        self.lpq.push(time, callback, args)

    def _schedule_hp(self, func, callback, *args):
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
            tnow = self.time()
            # Schedule a LP task if no normal task is ready
            l = len(self.lpq)
            if (l and not self.schedule_lp_task(cur_task, tnow)) or l == 0:
                # Expire entries in waitq and move them to runq
                while self.waitq:
                    t = self.waitq.peektime()
                    delay = time.ticks_diff(t, tnow)
                    if delay > 0:
                        break
                    self.waitq.pop(cur_task)
                    if __debug__ and DEBUG:
                        log.debug("Moving from waitq to runq: %s", cur_task[1])
                    self.call_soon(cur_task[1], *cur_task[2])

            # Process runq
            l = len(self.runq)
            if __debug__ and DEBUG:
                log.debug("Entries in runq: %d", l)
            while l:
                # Check list of high priority tasks
                cb = None
                for entry in self.hp_tasks:
                    if entry[0] and entry[0]():  # Ready to run
                        entry[0] = 0
                        cb = entry[1]
                        args = entry[2]
                        break

                if cb is None:
                    cb = self.runq.popleft()
                    l -= 1
                    args = ()
                    if not isinstance(cb, type_gen):
                        args = self.runq.popleft()
                        l -= 1
                        if __debug__ and DEBUG:
                            log.info("Next callback to run: %s", (cb, args))
                        cb(*args)
                        continue

                if __debug__ and DEBUG:
                    log.info("Next coroutine to run: %s", (cb, args))
                self.cur_task = cb
                delay = 0
                func = None
                low_priority = False  # Assume normal priority
                try:
                    if args is ():
                        ret = next(cb)
                    else:
                        ret = cb.send(*args)
                    if __debug__ and DEBUG:
                        log.info("Coroutine %s yield result: %s", cb, ret)
                    if isinstance(ret, SysCall1):
                        arg = ret.arg
                        if isinstance(ret, SleepMs):
                            delay = arg
                            if isinstance(ret, AfterMs):
                                low_priority = True
                                if isinstance(ret, After):
                                    delay = int(delay*1000)
                            elif isinstance(ret, When):
                                if callable(arg):
                                    func = arg
                                else:
                                    assert False, "Argument to 'when' must be a function or method."
                        elif isinstance(ret, IORead):
                            cb.pend_throw(False)
                            self.add_reader(arg, cb)
                            continue
                        elif isinstance(ret, IOWrite):
                            cb.pend_throw(False)
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
                except CancelledError as e:
                    if __debug__ and DEBUG:
                        log.debug("Coroutine cancelled: %s", cb)
                    continue
                if func is not None:
                    self._schedule_hp(func, cb)
                    continue
                # Currently all syscalls don't return anything, so we don't
                # need to feed anything to the next invocation of coroutine.
                # If that changes, need to pass that value below.
                if low_priority:
                    self.call_after_ms(delay, cb)  # Put on lpq
                elif delay:
                    self.call_later_ms(delay, cb)  # waitq
                else:
                    self.call_soon(cb)  # runq

            # Wait until next waitq task or I/O availability
            delay = 0
            if not self.runq:
                delay = -1
                tnow = self.time()
                if self.waitq:
                    t = self.waitq.peektime()
                    delay = time.ticks_diff(t, tnow)
                    if delay < 0:
                        delay = 0
                if self.lpq:
                    t = self.lpq.peektime()
                    lpdelay = time.ticks_diff(t, tnow)
                    if lpdelay < 0:
                        lpdelay = 0
                    if lpdelay < delay or delay < 0:
                        delay = lpdelay
            self.wait(delay)

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
def get_event_loop(runq_len=16, waitq_len=16, lpqlen=16):
    if uasyncio.core._event_loop is None:  # Add a q entry for lp_monitor()
        uasyncio.core._event_loop = uasyncio.core._event_loop_class(runq_len, waitq_len, lpqlen)
    return uasyncio.core._event_loop
