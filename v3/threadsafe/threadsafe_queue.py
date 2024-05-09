# threadsafe_queue.py Provides ThreadsafeQueue class

# Copyright (c) 2022 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Uses pre-allocated ring buffer: can use list or array
# Asynchronous iterator allowing consumer to use async for

import asyncio


class ThreadSafeQueue:  # MicroPython optimised
    def __init__(self, buf):
        self._q = [0 for _ in range(buf)] if isinstance(buf, int) else buf
        self._size = len(self._q)
        self._wi = 0
        self._ri = 0
        self._evput = asyncio.ThreadSafeFlag()  # Triggered by put, tested by get
        self._evget = asyncio.ThreadSafeFlag()  # Triggered by get, tested by put

    def full(self):
        return ((self._wi + 1) % self._size) == self._ri

    def empty(self):
        return self._ri == self._wi

    def qsize(self):
        return (self._wi - self._ri) % self._size

    def get_sync(self, block=False):  # Remove and return an item from the queue.
        if not block and self.empty():
            raise IndexError  # Not allowed to block
        while self.empty():  # Block until an item appears
            pass
        r = self._q[self._ri]
        self._ri = (self._ri + 1) % self._size
        self._evget.set()
        return r

    def put_sync(self, v, block=False):
        self._q[self._wi] = v
        self._evput.set()  # Schedule task waiting on get
        if not block and self.full():
            raise IndexError
        while self.full():
            pass  # can't bump ._wi until an item is removed
        self._wi = (self._wi + 1) % self._size

    async def put(self, val):  # Usage: await queue.put(item)
        while self.full():  # Queue full
            await self._evget.wait()
        self.put_sync(val)

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.get()

    async def get(self):
        while self.empty():
            await self._evput.wait()
        r = self._q[self._ri]
        self._ri = (self._ri + 1) % self._size
        self._evget.set()  # Schedule task waiting on ._evget
        return r
