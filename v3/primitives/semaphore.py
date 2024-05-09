# semaphore.py

# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import asyncio

# A Semaphore is typically used to limit the number of coros running a
# particular piece of code at once. The number is defined in the constructor.
class Semaphore:
    def __init__(self, value=1):
        self._count = value
        self._event = asyncio.Event()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        self.release()
        await asyncio.sleep(0)

    async def acquire(self):
        self._event.clear()
        while self._count == 0:  # Multiple tasks may be waiting for
            await self._event.wait()  # a release
            self._event.clear()
            # When we yield, another task may succeed. In this case
            await asyncio.sleep(0)  # the loop repeats
        self._count -= 1

    def release(self):
        self._event.set()
        self._count += 1


class BoundedSemaphore(Semaphore):
    def __init__(self, value=1):
        super().__init__(value)
        self._initial_value = value

    def release(self):
        if self._count < self._initial_value:
            super().release()
        else:
            raise ValueError("Semaphore released more than acquired")
