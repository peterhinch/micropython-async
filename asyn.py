# asyn.py 'micro' synchronisation primitives for uasyncio
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license
# Test/demo programs asyntest.py, barrier_test.py
# Provides Lock, Event and Barrier classes and launch function
# Now uses low_priority where available and appropriate.

# CPython 3.5 compatibility
# (ignore RuntimeWarning: coroutine '_g' was never awaited)

# Check availability of 'priority' version
try:
    import asyncio_priority as asyncio
    p_version = True
except ImportError:
    p_version = False
    try:
        import uasyncio as asyncio
    except ImportError:
        import asyncio

after = asyncio.after if p_version else asyncio.sleep

async def _g():
    pass
type_coro = type(_g())

# If a callback is passed, run it and return.
# If a coro is passed initiate it and return.
# coros are passed by name i.e. not using function call syntax.
def launch(func, tup_args):
    res = func(*tup_args)
    if isinstance(res, type_coro):
        loop = asyncio.get_event_loop()
        loop.create_task(res)


# To access a lockable resource a coro should issue
# async with lock_instance:
#    access the locked resource

# Alternatively:
# await lock.acquire()
# try:
#   do stuff with locked resource
# finally:
#   lock.release
# Uses normal scheduling on assumption that locks are held briefly.
class Lock():
    def __init__(self, delay_ms=0):
        self._locked = False
        self.delay_ms = delay_ms

    def locked(self):
        return self._locked

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, *args):
        self.release()
        await asyncio.sleep(0)

    async def acquire(self):
        while True:
            if self._locked:
                await asyncio.sleep_ms(self.delay_ms)
            else:
                self._locked = True
                break

    def release(self):
        if not self._locked:
            raise RuntimeError('Attempt to release a lock which has not been set')
        self._locked = False


# A coro waiting on an event issues await event
# A coro rasing the event issues event.set()
# When all waiting coros have run
# event.clear() should be issued
# Use of low_priority may be specified in the constructor
# when it will be used if available.
class Event():
    def __init__(self, lp=False):
        self.after = after if (p_version and lp) else asyncio.sleep
        self.clear()

    def clear(self):
        self._flag = False
        self._data = None

    def __await__(self):
        while not self._flag:
            yield from self.after(0)

    __iter__ = __await__

    def is_set(self):
        return self._flag

    def set(self, data=None):
        self._flag = True
        self._data = data

    def value(self):
        return self._data

# A Barrier synchronises N coros. Each issues await barrier
# execution pauses until all other participant coros are waiting on it.
# At that point the callback is executed. Then the barrier is 'opened' and
# excution of all participants resumes.
# Uses low_priority if available
class Barrier():
    def __init__(self, participants, func=None, args=()):
        self._participants = participants
        self._func = func
        self._args = args
        self._reset(True)

    def __await__(self):
        self._update()
        if self._at_limit():  # All other threads are also at limit
            if self._func is not None:
                launch(self._func, self._args)
            self._reset(not self._down)
            return

        direction = self._down
        while True:  # Wait until last waiting thread changes the direction
            if direction != self._down:
                return
            yield from after(0)

    __iter__ = __await__

    def _reset(self, down):
        self._down = down
        self._count = self._participants if down else 0

    def _at_limit(self):
        limit = 0 if self._down else self._participants
        return self._count == limit

    def _update(self):
        self._count += -1 if self._down else 1
        if self._count < 0 or self._count > self._participants:
            raise ValueError('Too many threads accessing Barrier')

# A Semaphore is typically used to limit the number of coros running a
# particular piece of code at once. The number is defined in the constructor.
class Semaphore():
    def __init__(self, value=1):
        self._count = value

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, *args):
        self.release()
        await asyncio.sleep(0)

    async def acquire(self):
        while self._count == 0:
            await after(0)
        self._count -= 1

    def release(self):
        self._count += 1

class BoundedSemaphore(Semaphore):
    def __init__(self, value=1):
        super().__init__(value)
        self._initial_value = value

    def release(self):
        if self._count < self._initial_value:
            self._count += 1
        else:
            raise ValueError('Semaphore released more than acquired')

# uasyncio does not have a mechanism whereby a task can be terminated by another.
# This can cause an issue if a task instantiates other tasks then terminates:
# the child tasks continue to run, which may not be desired. The ExitGate helps
# in managing this. The parent instantiates an ExitGate and makes it available
# to the children. The latter use it as a context manager and can poll the
# ending method to check if it's necessary to terminate. The parent issues
# await exit_gate_instance
# before terminating. Termination will pause until all children have completed.

class ExitGate():
    def __init__(self, granularity=100):
        self._ntasks = 0
        self._ending = False
        self._granularity = granularity

    def ending(self):
        return self._ending

    def __await__(self):
        self._ending = True
        while self._ntasks:
            yield from asyncio.sleep_ms(self._granularity)
        self._ending = False  # May want to re-use

    __iter__ = __await__

    async def __aenter__(self):
        self._ntasks += 1
        await asyncio.sleep_ms(0)

    async def __aexit__(self, *args):
        self._ntasks -= 1
        await asyncio.sleep_ms(0)

    # Sleep while checking for premature ending. Return True on normal ending,
    # False if premature.
    async def sleep(self, t):
        t *= 1000  # ms
        granularity = self._granularity
        if t <= granularity:
            await asyncio.sleep_ms(t)
        else:
            n, rem = divmod(t, granularity)
            for _ in range(n):
                if self._ending:
                    return False
                await asyncio.sleep_ms(granularity)
            if self._ending:
                return False
            await asyncio.sleep_ms(rem)
        return not self._ending
