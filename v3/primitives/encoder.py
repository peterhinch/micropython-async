# encoder.py Asynchronous driver for incremental quadrature encoder.

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# This driver is intended for encoder-based control knobs. It is not
# suitable for NC machine applications. Please see the docs.

import uasyncio as asyncio
from machine import Pin

class Encoder:
    LATENCY = 50

    def __init__(self, pin_x, pin_y, v=0, vmin=None, vmax=None,
                 callback=lambda a, b : None, args=()):
        self._pin_x = pin_x
        self._pin_y = pin_y
        self._v = v
        self._tsf = asyncio.ThreadSafeFlag()
        try:
            xirq = pin_x.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._x_cb, hard=True)
            yirq = pin_y.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._y_cb, hard=True)
        except TypeError:
            xirq = pin_x.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._x_cb)
            yirq = pin_y.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._y_cb)
        asyncio.create_task(self._run(vmin, vmax, callback, args))


    # Hardware IRQ's
    def _x_cb(self, pin):
        fwd = pin() ^ self._pin_y()
        self._v += 1 if fwd else -1
        self._tsf.set()

    def _y_cb(self, pin):
        fwd = pin() ^ self._pin_x() ^ 1
        self._v += 1 if fwd else -1
        self._tsf.set()

    async def _run(self, vmin, vmax, cb, args):
        pv = self._v  # Prior value
        while True:
            await self._tsf.wait()
            cv = self._v  # Current value
            if vmax is not None:
                cv = min(cv, vmax)
            if vmin is not None:
                cv = max(cv, vmin)
            self._v = cv
            #print(cv, pv)
            if cv != pv:
                cb(cv, cv - pv, *args)  # User CB in uasyncio context
                pv = cv
            await asyncio.sleep_ms(self.LATENCY)

    def value(self):
        return self._v
