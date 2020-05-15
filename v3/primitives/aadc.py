# aadc.py AADC (asynchronous ADC) class

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
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
        self._sreader = asyncio.StreamReader(self)

    def __iter__(self):
        b = await self._sreader.read(2)
        return int.from_bytes(b, 'little')

    # If normal will pause until ADC value is in range
    # Otherwise will pause until value is out of range
    def sense(self, normal):
        self._pol = normal

    def read_u16(self):
        return self._adc.read_u16()

    # Call syntax: set limits for trigger
    # lower is None: leave limits unchanged.
    # upper is None: treat lower as relative to current value.
    # both have values: treat as absolute limits.
    def __call__(self, lower=None, upper=None):
        if lower is not None:
            if upper is None:  # Relative limit
                r = self._adc.read_u16()
                self._lower = r - lower
                self._upper = r + lower
            else:  # Absolute limits
                self._lower = lower
                self._upper = upper
        return self

    def read(self, n):
        return int.to_bytes(self._adc.read_u16(), 2, 'little')

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                if self._pol ^ (self._lower <= self._adc.read_u16() <= self._upper):
                    ret |= MP_STREAM_POLL_RD
        return ret
