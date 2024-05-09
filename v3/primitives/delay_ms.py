# delay_ms.py Now uses ThreadSafeFlag and has extra .wait() API
# Usage:
# from primitives import Delay_ms

# Copyright (c) 2018-2022 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import asyncio
from utime import ticks_add, ticks_diff, ticks_ms
from . import launch


class Delay_ms:
    class DummyTimer:  # Stand-in for the timer class. Can be cancelled.
        def cancel(self):
            pass

    _fake = DummyTimer()

    def __init__(self, func=None, args=(), duration=1000):
        self._func = func
        self._args = args
        self._durn = duration  # Default duration
        self._retn = None  # Return value of launched callable
        self._tend = None  # Stop time (absolute ms).
        self._busy = False
        self._trig = asyncio.ThreadSafeFlag()
        self._tout = asyncio.Event()  # Timeout event
        self.wait = self._tout.wait  # Allow: await wait_ms.wait()
        self.clear = self._tout.clear
        self.set = self._tout.set
        self._ttask = self._fake  # Timer task
        self._mtask = asyncio.create_task(self._run())  # Main task

    async def _run(self):
        while True:
            await self._trig.wait()  # Await a trigger
            self._ttask.cancel()  # Cancel and replace
            await asyncio.sleep_ms(0)
            dt = max(ticks_diff(self._tend, ticks_ms()), 0)  # Beware already elapsed.
            self._ttask = asyncio.create_task(self._timer(dt))

    async def _timer(self, dt):
        await asyncio.sleep_ms(dt)
        self._tout.set()  # Only gets here if not cancelled.
        self._busy = False
        if self._func is not None:
            self._retn = launch(self._func, self._args)

    # API
    # trigger may be called from hard ISR.
    def trigger(self, duration=0):  # Update absolute end time, 0-> ctor default
        if self._mtask is None:
            raise RuntimeError("Delay_ms.deinit() has run.")
        self._tend = ticks_add(ticks_ms(), duration if duration > 0 else self._durn)
        self._retn = None  # Default in case cancelled.
        self._busy = True
        self._trig.set()

    def stop(self):
        self._ttask.cancel()
        self._ttask = self._fake
        self._busy = False
        self._tout.clear()

    def __call__(self):  # Current running status
        return self._busy

    running = __call__

    def rvalue(self):
        return self._retn

    def callback(self, func=None, args=()):
        self._func = func
        self._args = args

    def deinit(self):
        if self._mtask is not None:  # https://github.com/peterhinch/micropython-async/issues/98
            self.stop()
            self._mtask.cancel()
            self._mtask = None
