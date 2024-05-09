# threadsafe_queue.py Provides ThreadsafeQueue class

# Copyright (c) 2022 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import asyncio


class ThreadSafeEvent(asyncio.Event):
    def __init__(self):
        super().__init__()
        self._waiting_on_tsf = False
        self._tsf = asyncio.ThreadSafeFlag()

    def set(self):
        self._tsf.set()

    async def _waiter(self):
        await self._tsf.wait()
        super().set()
        self._waiting_on_tsf = False

    async def wait(self):
        if self._waiting_on_tsf == False:
            self._waiting_on_tsf = True
            await asyncio.sleep_ms(0)
            try:
                await self._tsf.wait()
                super().set()
                self._waiting_on_tsf = False
            except asyncio.CancelledError:
                asyncio.create_task(self._waiter())
                raise
        else:
            await super().wait()
