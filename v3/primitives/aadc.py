# aadc.py AADC (asynchronous ADC) class

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import asyncio
import io

MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)


class AADC(io.IOBase):
    def __init__(self, adc):
        self._adc = adc
        self._lower = 0
        self._upper = 65535
        self._pol = True
        self._last = None
        self._sreader = asyncio.StreamReader(self)

    def __iter__(self):
        b = yield from self._sreader.read(2)
        return int.from_bytes(b, "little")

    def _adcread(self):
        self._last = self._adc.read_u16()
        return self._last

    def read(self, n):  # For use by StreamReader only
        return int.to_bytes(self._last, 2, "little")

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                if self._pol ^ (self._lower <= self._adcread() <= self._upper):
                    ret |= MP_STREAM_POLL_RD
        return ret

    # *** API ***

    # If normal will pause until ADC value is in range
    # Otherwise will pause until value is out of range
    def sense(self, normal):
        self._pol = normal

    def read_u16(self, last=False):
        if last:
            return self._last
        return self._adcread()

    # Call syntax: set limits for trigger
    # lower is None: leave limits unchanged.
    # upper is None: treat lower as relative to current value.
    # both have values: treat as absolute limits.
    def __call__(self, lower=None, upper=None):
        if lower is not None:
            if upper is None:  # Relative limit
                r = self._adcread() if self._last is None else self._last
                self._lower = r - lower
                self._upper = r + lower
            else:  # Absolute limits
                self._lower = lower
                self._upper = upper
        return self
