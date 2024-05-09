# encoder.py Asynchronous driver for incremental quadrature encoder.

# Copyright (c) 2021-2023 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# For an explanation of the design please see
# [ENCODERS.md](https://github.com/peterhinch/micropython-samples/blob/master/encoders/ENCODERS.md)

# Thanks are due to the following collaborators:
# @ilium007 for identifying the issue of tracking detents,
# https://github.com/peterhinch/micropython-async/issues/82.

# Mike Teachman (@miketeachman) for design discussions and testing
# against a state table design
# https://github.com/miketeachman/micropython-rotary/blob/master/rotary.py

# Raul Kompaß (@rkompass) for suggesting a bugfix here
# https://forum.micropython.org/viewtopic.php?f=15&t=9929&p=66175#p66156

import asyncio
from machine import Pin
from select import poll, POLLIN


def ready(tsf, poller):
    r = (tsf, POLLIN)
    poller.register(*r)

    def is_rdy():
        return r in poller.ipoll(0)

    return is_rdy


class Encoder:
    def __init__(
        self,
        pin_x,
        pin_y,
        v=0,
        div=1,
        vmin=None,
        vmax=None,
        mod=None,
        callback=lambda a, b: None,
        args=(),
        delay=100,
    ):
        self._pin_x = pin_x
        self._pin_y = pin_y
        self._x = pin_x()
        self._y = pin_y()
        self._v = v * div  # Initialise hardware value
        self._cv = v  # Current (divided) value
        self.delay = delay  # Pause (ms) for motion to stop/limit callback frequency
        self._trig = asyncio.Event()

        if ((vmin is not None) and v < vmin) or ((vmax is not None) and v > vmax):
            raise ValueError("Incompatible args: must have vmin <= v <= vmax")
        self._tsf = asyncio.ThreadSafeFlag()
        self._tsf_ready = ready(self._tsf, poll())  # Create a ready function
        trig = Pin.IRQ_RISING | Pin.IRQ_FALLING
        try:
            xirq = pin_x.irq(trigger=trig, handler=self._x_cb, hard=True)
            yirq = pin_y.irq(trigger=trig, handler=self._y_cb, hard=True)
        except TypeError:  # hard arg is unsupported on some hosts
            xirq = pin_x.irq(trigger=trig, handler=self._x_cb)
            yirq = pin_y.irq(trigger=trig, handler=self._y_cb)
        asyncio.create_task(self._run(vmin, vmax, div, mod, callback, args))

    # Hardware IRQ's. Duration 36μs on Pyboard 1 ~50μs on ESP32.
    # IRQ latency: 2nd edge may have occured by the time ISR runs, in
    # which case there is no movement.
    def _x_cb(self, pin_x):
        if (x := pin_x()) != self._x:
            self._x = x
            self._v += 1 if x ^ self._pin_y() else -1
            self._tsf.set()

    def _y_cb(self, pin_y):
        if (y := pin_y()) != self._y:
            self._y = y
            self._v -= 1 if y ^ self._pin_x() else -1
            self._tsf.set()

    async def _run(self, vmin, vmax, div, mod, cb, args):
        pv = self._v  # Prior hardware value
        pcv = self._cv  # Prior divided value passed to callback
        lcv = pcv  # Current value after limits applied
        plcv = pcv  # Previous value after limits applied
        delay = self.delay
        while True:
            if delay > 0 and self._tsf_ready():  # Ensure ThreadSafeFlag is clear
                await self._tsf.wait()
            await self._tsf.wait()
            await asyncio.sleep_ms(delay)  # Wait for motion to stop.
            hv = self._v  # Sample hardware (atomic read).
            if hv == pv:  # A change happened but was negated before
                continue  # this got scheduled. Nothing to do.
            pv = hv
            cv = round(hv / div)  # cv is divided value.
            if not (dv := cv - pcv):  # dv is change in divided value.
                continue  # No change
            lcv += dv  # lcv: divided value with limits/mod applied
            lcv = lcv if vmax is None else min(vmax, lcv)
            lcv = lcv if vmin is None else max(vmin, lcv)
            lcv = lcv if mod is None else lcv % mod
            self._cv = lcv  # update ._cv for .value() before CB.
            if lcv != plcv:
                cb(lcv, lcv - plcv, *args)  # Run user CB in uasyncio context
                self._trig.set()  # Enable async iterator
            pcv = cv
            plcv = lcv

    def __aiter__(self):
        return self

    def __anext__(self):
        await self._trig.wait()
        self._trig.clear()
        return self._cv

    def value(self):
        return self._cv
