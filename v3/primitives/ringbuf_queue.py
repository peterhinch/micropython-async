# ringbuf_queue.py Provides RingbufQueue class

# Copyright (c) 2022-2023 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# API differs from CPython
# Uses pre-allocated ring buffer: can use list or array
# Asynchronous iterator allowing consumer to use async for
# put_nowait QueueFull exception can be ignored allowing oldest data to be discarded.

import asyncio


class RingbufQueue:  # MicroPython optimised
    def __init__(self, buf):
        self._q = [0 for _ in range(buf)] if isinstance(buf, int) else buf
        self._size = len(self._q)
        self._wi = 0
        self._ri = 0
        self._evput = asyncio.Event()  # Triggered by put, tested by get
        self._evget = asyncio.Event()  # Triggered by get, tested by put

    def full(self):
        return ((self._wi + 1) % self._size) == self._ri

    def empty(self):
        return self._ri == self._wi

    def qsize(self):
        return (self._wi - self._ri) % self._size

    def get_nowait(self):  # Remove and return an item from the queue.
        # Return an item if one is immediately available, else raise QueueEmpty.
        if self.empty():
            raise IndexError
        r = self._q[self._ri]
        self._ri = (self._ri + 1) % self._size
        self._evget.set()  # Schedule all tasks waiting on ._evget
        self._evget.clear()
        return r

    def peek(self):  # Return oldest item from the queue without removing it.
        # Return an item if one is immediately available, else raise QueueEmpty.
        if self.empty():
            raise IndexError
        return self._q[self._ri]

    def put_nowait(self, v):
        self._q[self._wi] = v
        self._evput.set()  # Schedule any tasks waiting on get
        self._evput.clear()
        self._wi = (self._wi + 1) % self._size
        if self._wi == self._ri:  # Would indicate empty
            self._ri = (self._ri + 1) % self._size  # Discard a message
            raise IndexError  # Caller can ignore if overwrites are OK

    async def put(self, val):  # Usage: await queue.put(item)
        while self.full():  # Queue full
            await self._evget.wait()  # May be >1 task waiting on ._evget
            # Task(s) waiting to get from queue, schedule first Task
        self.put_nowait(val)

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.get()

    async def get(self):
        while self.empty():  # Empty. May be more than one task waiting on ._evput
            await self._evput.wait()
        r = self._q[self._ri]
        self._ri = (self._ri + 1) % self._size
        self._evget.set()  # Schedule all tasks waiting on ._evget
        self._evget.clear()
        return r
