# threadsafe_queue.py Provides ThreadsafeQueue class

# Copyright (c) 2022 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Uses pre-allocated ring buffer: can use list or array
# Asynchronous iterator allowing consumer to use async for
# put_nowait QueueFull exception can be ignored allowing oldest data to be discarded.

import uasyncio as asyncio


class ThreadSafeQueue:  # MicroPython optimised
    def __init__(self, buf):
        self._q = buf
        self._size = len(buf)
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
        # Return an item if one is immediately available, else raise QueueEmpty.
        if block:
            while self.empty():
                pass
        else:
            if self.empty():
                raise IndexError
        r = self._q[self._ri]
        self._ri = (self._ri + 1) % self._size
        self._evget.set()
        return r

    def put_sync(self, v, block=False):
        self._q[self._wi] = v
        self._evput.set()  # Schedule any tasks waiting on get
        if block:
            while ((self._wi + 1) % self._size) == self._ri:
                pass  # can't bump ._wi until an item is removed
        elif ((self._wi + 1) % self._size) == self._ri:
            raise IndexError
        self._wi = (self._wi + 1) % self._size

    async def put(self, val):  # Usage: await queue.put(item)
        while self.full():  # Queue full
            await self._evget.wait()  # May be >1 task waiting on ._evget
            # Task(s) waiting to get from queue, schedule first Task
        self.put_sync(val)

    def __aiter__(self):
        return self

    async def __anext__(self):
        while self.empty():  # Empty. May be more than one task waiting on ._evput
            await self._evput.wait()
        r = self._q[self._ri]
        self._ri = (self._ri + 1) % self._size
        self._evget.set()  # Schedule all tasks waiting on ._evget
        return r
