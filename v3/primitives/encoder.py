# encoder.py Asynchronous driver for incremental quadrature encoder.

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# This driver is intended for encoder-based control knobs. It is not
# suitable for NC machine applications. Please see the docs.

import uasyncio as asyncio

class Encoder:
    def __init__(self, pin_x, pin_y, v=0, vmin=None, vmax=None,
                 callback=lambda a, b : None, args=()):
        self._v = v
        asyncio.create_task(self._run(pin_x, pin_y, vmin, vmax,
                                      callback, args))

    def _run(self, pin_x, pin_y, vmin, vmax, callback, args):
        xp = pin_x()  # Prior levels
        yp = pin_y()
        pf = None  # Prior direction
        while True:
            await asyncio.sleep_ms(0)
            x = pin_x()  # Current levels
            y = pin_y()
            if xp == x:
                if yp == y:
                    continue  # No change, nothing to do
                fwd = x ^ y ^ 1  # y changed
            else:
                fwd = x ^ y  # x changed
            pv = self._v  # Cache prior value
            nv = pv + (1 if fwd else -1)  # New value
            if vmin is not None:
                nv = max(vmin, nv)
            if vmax is not None:
                nv = min(vmax, nv)
            if nv != pv:  # Change
                rev = (pf is not None) and (pf != fwd)
                if not rev:
                    callback(nv, fwd, *args)
                    self._v = nv

            pf = fwd  # Update prior state
            xp = x
            yp = y

    def value(self):
        return self._v
