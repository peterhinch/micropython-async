# encoder.py Asynchronous driver for incremental quadrature encoder.

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# This driver is intended for encoder-based control knobs. It is
# unsuitable for NC machine applications. Please see the docs.

import uasyncio as asyncio
from machine import Pin

class Encoder:
    delay = 100  # Pause (ms) for motion to stop

    def __init__(self, pin_x, pin_y, v=0, vmin=None, vmax=None, div=1,
                 callback=lambda a, b : None, args=()):
        self._pin_x = pin_x
        self._pin_y = pin_y
        self._v = 0  # Hardware value always starts at 0
        self._cv = v  # Current (divided) value
        if ((vmin is not None) and v < min) or ((vmax is not None) and v > vmax):
            raise ValueError('Incompatible args: must have vmin <= v <= vmax')
        self._tsf = asyncio.ThreadSafeFlag()
        trig = Pin.IRQ_RISING | Pin.IRQ_FALLING
        try:
            xirq = pin_x.irq(trigger=trig, handler=self._x_cb, hard=True)
            yirq = pin_y.irq(trigger=trig, handler=self._y_cb, hard=True)
        except TypeError:  # hard arg is unsupported on some hosts
            xirq = pin_x.irq(trigger=trig, handler=self._x_cb)
            yirq = pin_y.irq(trigger=trig, handler=self._y_cb)
        asyncio.create_task(self._run(vmin, vmax, div, callback, args))

    # Hardware IRQ's
    def _x_cb(self, pin):
        fwd = pin() ^ self._pin_y()
        self._v += 1 if fwd else -1
        self._tsf.set()

    def _y_cb(self, pin):
        fwd = pin() ^ self._pin_x() ^ 1
        self._v += 1 if fwd else -1
        self._tsf.set()

    async def _run(self, vmin, vmax, div, cb, args):
        pv = self._v  # Prior hardware value
        cv = self._cv  # Current divided value as passed to callback
        pcv = cv  # Prior divided value passed to callback
        mod = 0
        delay = self.delay
        while True:
            await self._tsf.wait()
            await asyncio.sleep_ms(delay)  # Wait for motion to stop
            new = self._v  # Sample hardware (atomic read)
            a = new - pv  # Hardware change
            # Ensure symmetrical bahaviour for + and - values
            q, r = divmod(abs(a), div)
            if a < 0:
                r = -r
                q = -q
            pv = new - r  # Hardware value when local value was updated
            cv += q
            if vmax is not None:
                cv = min(cv, vmax)
            if vmin is not None:
                cv = max(cv, vmin)
            self._cv = cv  # For value()
            if cv != pcv:
                cb(cv, cv - pcv, *args)  # User CB in uasyncio context
            pcv = cv

    def value(self):
        return self._cv
