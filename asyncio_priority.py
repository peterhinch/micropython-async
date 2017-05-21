# asyncio_priority.py Modified version of uasyncio with priority mechanism.
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license

import utime as time
import utimeq
from uasyncio import *

class PriorityEventLoop(PollEventLoop):
    def __init__(self, len=42, lpqlen=42, max_overdue_ms=0, hpqlen=0):
        super().__init__(len)
        self._max_overdue_ms = max_overdue_ms
        self.lpq = utimeq.utimeq(lpqlen)
        if hpqlen:
            self.hpq = [[0,0,0] for _ in range(hpqlen)]
        else:
            self.hpq = None

    def max_overdue_ms(self, t=None):
        if t is not None:
            self._max_overdue_ms = t
        return self._max_overdue_ms

    def call_after_ms(self, delay, callback, args=()):
        # low priority.
        t = time.ticks_add(self.time(), delay)
        if __debug__ and DEBUG:
            log.debug("Scheduling LP %s", (time, callback, args))
        self.lpq.push(t, callback, args)

    def call_after(self, delay, callback, *args):
        # low priority.
        t = time.ticks_add(self.time(), int(delay * 1000))
        if __debug__ and DEBUG:
            log.debug("Scheduling LP %s", (time, callback, args))
        self.lpq.push(t, callback, args)

    def _schedule_hp(self, func, callback, args=()):
        if self.hpq is None:
            self.hpq = [func, callback, args]
        else:  # Try to assign without allocation
            for entry in self.hpq:
                if not entry[0]:
                    entry[0] = func
                    entry[1] = callback
                    entry[2] = args
                    break
            else:
                self.hpq.append([func, callback, args])

    def run_forever(self):
        cur_task = [0, 0, 0]
        while True:
            if self.q:
                # wait() may finish prematurely due to I/O completion,
                # and schedule new, earlier than before tasks to run.
                while 1:
                    # Check high priority queue
                    if self.hpq is not None:
                        hp_found = False
                        for entry in self.hpq:
                            if entry[0] and entry[0]():
                                hp_found = True
                                entry[0] = 0
                                cur_task[0] = 0
                                cur_task[1] = entry[1] # ??? quick non-allocating copy
                                cur_task[2] = entry[2]
                                break
                        if hp_found:
                            break
                    # Schedule most overdue LP coro
                    tnow = self.time()
                    if self.lpq and self._max_overdue_ms > 0:
                        t = self.lpq.peektime()
                        overdue = -time.ticks_diff(t, tnow)
                        if overdue > self._max_overdue_ms:
                            self.lpq.pop(cur_task)
                            break
                    # Schedule any due normal task
                    t = self.q.peektime()
                    delay = time.ticks_diff(t, tnow)
                    if delay <= 0:
                        self.q.pop(cur_task)
                        break
                    # Schedule any due LP task
                    if self.lpq:
                        t = self.lpq.peektime()
                        lpdelay = time.ticks_diff(t, tnow)
                        if lpdelay <= 0:
                            self.lpq.pop(cur_task)
                            break
                        delay = min(delay, lpdelay)
                    self.wait(delay)  # superclass
                t = cur_task[0]
                cb = cur_task[1]
                args = cur_task[2]
                if __debug__ and DEBUG:
                    log.debug("Next coroutine to run: %s", (t, cb, args))
#                __main__.mem_info()
            else:  # Normal q is empty
                ready = False
                if self.lpq:
                    t = self.lpq.peektime()
                    delay = time.ticks_diff(t, self.time())
                    if delay <= 0:
                        self.lpq.pop(cur_task)
                        t = cur_task[0]
                        cb = cur_task[1]
                        args = cur_task[2]
                        if __debug__ and DEBUG:
                            log.debug("Next coroutine to run: %s", (t, cb, args))
                        ready = True
                if not ready:
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
                        ret = next(cb)
                    else:
                        ret = cb.send(*args)
                    if __debug__ and DEBUG:
                        log.debug("Coroutine %s yield result: %s", cb, ret)
                    if isinstance(ret, SysCall1):
                        arg = ret.arg
                        if isinstance(ret, AfterMs):
                            priority = False
                        if isinstance(ret, Sleep) or isinstance(ret, After):
                            delay = int(arg * 1000)
                        elif isinstance(ret, When):
                            if callable(arg):
                                func = arg
                            else:
                                assert False, "Argument to 'when' must be a function or method."
                        elif isinstance(ret, SleepMs):
                            delay = arg
                        elif isinstance(ret, IORead):
#                            self.add_reader(ret.obj.fileno(), lambda self, c, f: self.call_soon(c, f), self, cb, ret.obj)
#                            self.add_reader(ret.obj.fileno(), lambda c, f: self.call_soon(c, f), cb, ret.obj)
#                            self.add_reader(arg.fileno(), lambda cb: self.call_soon(cb), cb)
                            self.add_reader(arg, cb)
                            continue
                        elif isinstance(ret, IOWrite):
#                            self.add_writer(arg.fileno(), lambda cb: self.call_soon(cb), cb)
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
                    else:
                        assert False, "Unsupported coroutine yield value: %r (of type %r)" % (ret, type(ret))
                except StopIteration as e:
                    if __debug__ and DEBUG:
                        log.debug("Coroutine finished: %s", cb)
                    continue
                if func is not None:
                    self._schedule_hp(func, cb, args)
                else:
                    if priority:
                        self.call_later_ms(delay, cb, args)
                    else:
                        self.call_after_ms(delay, cb, args)


class Sleep(SleepMs):
    pass

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

_event_loop = None
_event_loop_class = PriorityEventLoop
def get_event_loop(len=42, lpqlen=42, max_overdue_ms=0, hpqlen=0):
    global _event_loop
    if _event_loop is None:
        _event_loop = _event_loop_class(len, lpqlen, max_overdue_ms, hpqlen)
    return _event_loop
