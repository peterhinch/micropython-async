# asyn.py 'micro' synchronisation primitives for uasyncio
# Author: Peter Hinch
# Copyright Peter Hinch 2016 Released under the MIT license
# Test/demo program asyntest.py
# Provides Lock and Event classes

import uasyncio as asyncio

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
            yield
