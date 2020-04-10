# queue.py: adapted from uasyncio V2
# Code is based on Paul Sokolovsky's work.
# This is a temporary solution until uasyncio V3 gets an efficient official version

import uasyncio as asyncio


# Exception raised by get_nowait().
class QueueEmpty(Exception):
    pass


# Exception raised by put_nowait().
class QueueFull(Exception):
    pass

class Queue:

    def __init__(self, maxsize=0):
        self.maxsize = maxsize
        self._queue = []

    def _get(self):
        return self._queue.pop(0)

    async def get(self):  #  Usage: item = await queue.get()
        while self.empty():
            # Queue is empty, put the calling Task on the waiting queue
            await asyncio.sleep_ms(0)
        return self._get()

    def get_nowait(self):  # Remove and return an item from the queue.
        # Return an item if one is immediately available, else raise QueueEmpty.
        if self.empty():
            raise QueueEmpty()
        return self._get()

    def _put(self, val):
        self._queue.append(val)

    async def put(self, val):  # Usage: await queue.put(item)
        while self.qsize() >= self.maxsize and self.maxsize:
            # Queue full
            await asyncio.sleep_ms(0)
            # Task(s) waiting to get from queue, schedule first Task
        self._put(val)

    def put_nowait(self, val):  # Put an item into the queue without blocking.
        if self.qsize() >= self.maxsize and self.maxsize:
            raise QueueFull()
        self._put(val)

    def qsize(self):  # Number of items in the queue.
        return len(self._queue)

    def empty(self):  # Return True if the queue is empty, False otherwise.
        return len(self._queue) == 0

    def full(self):  # Return True if there are maxsize items in the queue.
        # Note: if the Queue was initialized with maxsize=0 (the default),
        # then full() is never True.

        if self.maxsize <= 0:
            return False
        else:
            return self.qsize() >= self.maxsize
