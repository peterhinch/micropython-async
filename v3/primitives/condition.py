# condition.py

# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

# Condition class
# from primitives.condition import Condition

class Condition():
    def __init__(self, lock=None):
        self.lock = asyncio.Lock() if lock is None else lock
        self.events = []

    async def acquire(self):
        await self.lock.acquire()

# enable this syntax:
# with await condition [as cond]:
    def __await__(self):
        await self.lock.acquire()
        return self

    __iter__ = __await__

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.lock.release()

    def locked(self):
        return self.lock.locked()

    def release(self):
        self.lock.release()  # Will raise RuntimeError if not locked

    def notify(self, n=1):  # Caller controls lock
        if not self.lock.locked():
            raise RuntimeError('Condition notify with lock not acquired.')
        for _ in range(min(n, len(self.events))):
            ev = self.events.pop()
            ev.set()

    def notify_all(self):
        self.notify(len(self.events))

    async def wait(self):
        if not self.lock.locked():
            raise RuntimeError('Condition wait with lock not acquired.')
        ev = asyncio.Event()
        self.events.append(ev)
        self.lock.release()
        await ev.wait()
        await self.lock.acquire()
        assert ev not in self.events, 'condition wait assertion fail'
        return True  # CPython compatibility

    async def wait_for(self, predicate):
        result = predicate()
        while not result:
            await self.wait()
            result = predicate()
        return result
