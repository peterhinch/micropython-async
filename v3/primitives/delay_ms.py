# delay_ms.py

# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file
# Rewritten for uasyncio V3. Allows stop time to be brought forwards.

import uasyncio as asyncio
from utime import ticks_add, ticks_diff, ticks_ms
from micropython import schedule
from . import launch
# Usage:
# from primitives.delay_ms import Delay_ms

class Delay_ms:
    verbose = False  # verbose and can_alloc retained to avoid breaking code.
    def __init__(self, func=None, args=(), can_alloc=True, duration=1000):
        self._func = func
        self._args = args
        self._duration = duration  # Default duration
        self._tstop = None  # Stop time (ms). None signifies not running.
        self._tsave = None  # Temporary storage for stop time
        self._ktask = None  # timer task
        self._retrn = None  # Return value of launched callable
        self._do_trig = self._trig  # Avoid allocation in .trigger

    def stop(self):
        if self._ktask is not None:
            self._ktask.cancel()

    def trigger(self, duration=0):  # Update end time
        now = ticks_ms()
        if duration <= 0:  # Use default set by constructor
            duration = self._duration
        self._retrn = None
        is_running = self()
        tstop = self._tstop  # Current stop time
        # Retriggering normally just updates ._tstop for ._timer
        self._tstop = ticks_add(now, duration)
        # Identify special case where we are bringing the end time forward
        can = is_running and duration < ticks_diff(tstop, now)
        if not is_running or can:
            schedule(self._do_trig, can)

    def _trig(self, can):
        if can:
            self._ktask.cancel()
        self._ktask = asyncio.create_task(self._timer(can))

    def __call__(self):  # Current running status
        return self._tstop is not None

    running = __call__

    def rvalue(self):
        return self._retrn

    async def _timer(self, restart):
        if restart:  # Restore cached end time
            self._tstop = self._tsave
        try:
            twait = ticks_diff(self._tstop, ticks_ms())
            while twait > 0:  # Must loop here: might be retriggered
                await asyncio.sleep_ms(twait)
                twait = ticks_diff(self._tstop, ticks_ms())
            if self._func is not None:  # Timed out: execute callback
                self._retrn = launch(self._func, self._args)
        finally:
            self._tsave = self._tstop  # Save in case we restart.
            self._tstop = None  # timer is stopped
