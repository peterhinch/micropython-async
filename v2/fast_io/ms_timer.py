# ms_timer.py A relatively high precision delay class for the fast_io version
# of uasyncio

import uasyncio as asyncio
import utime
import io
MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

class MillisecTimer(io.IOBase):
    def __init__(self):
        self.end = 0
        self.sreader = asyncio.StreamReader(self)

    def __iter__(self):
        await self.sreader.readline()

    def __call__(self, ms):
        self.end = utime.ticks_add(utime.ticks_ms(), ms)
        return self

    def readline(self):
        return b'\n'

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                if utime.ticks_diff(utime.ticks_ms(), self.end) >= 0:
                    ret |= MP_STREAM_POLL_RD
        return ret
