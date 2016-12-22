# asyn.py 'micro' synchronisation primitives for uasyncio
# Author: Peter Hinch
# Copyright Peter Hinch 2016 Released under the MIT license
# Test/demo programs asyntest.py, barrier_test.py
# Provides Lock, Event and Barrier classes and launch function

import uasyncio as asyncio

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
class Lock():
    def __init__(self):
        self._locked = False

    def locked(self):
        return self._locked

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, *args):
        self.release()
        await asyncio.sleep_ms(0)

    async def acquire(self):
        while True:
            if self._locked:
                await asyncio.sleep_ms(0)
            else:
                self._locked = True
                break

    def release(self):
        if not self._locked:
            raise RuntimeError('Attempt to release a lock which has not been set')
        self._locked = False


# A coro waiting on an event issues
# await event.wait()
# A coro wishing to flag coros waiting on the event issues
# event.set()
# When all waiting coros have run
# event.clear() should be issued
class Event():
    def __init__(self):
        self._flag = False

    def clear(self):
        self._flag = False

    def is_set(self):
        return self._flag

    def set(self):
        self._flag = True

    async def wait(self):
        while not self._flag:
            asyncio.sleep_ms(0)

class Barrier():
    def __init__(self, participants, func=None, args=()):
        self._participants = participants
        self._func = func
        self._args = args
        self._reset(True)

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

    async def signal_and_wait(self):
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
            await asyncio.sleep(0)

