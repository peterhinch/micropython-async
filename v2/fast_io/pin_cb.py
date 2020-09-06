# pin_cb.py Demo of device driver using fast I/O to schedule a callback
# PinCall class allows a callback to be associated with a change in pin state.

# This class is not suitable for switch I/O because of contact bounce:
# see Switch and Pushbutton classes in aswitch.py

import uasyncio as asyncio
import io
MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

class PinCall(io.IOBase):
    def __init__(self, pin, *, cb_rise=None, cbr_args=(), cb_fall=None, cbf_args=()):
        self.pin = pin
        self.cb_rise = cb_rise
        self.cbr_args = cbr_args
        self.cb_fall = cb_fall
        self.cbf_args = cbf_args
        self.pinval = pin.value()
        self.sreader = asyncio.StreamReader(self)
        loop = asyncio.get_event_loop()
        loop.create_task(self.run())

    async def run(self):
        while True:
            await self.sreader.read(1)

    def read(self, _):
        v = self.pinval
        if v and self.cb_rise is not None:
            self.cb_rise(*self.cbr_args)
            return b'\n'
        if not v and self.cb_fall is not None:
            self.cb_fall(*self.cbf_args)
        return b'\n'

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                v = self.pin.value()
                if v != self.pinval:
                    self.pinval = v
                    ret = MP_STREAM_POLL_RD
        return ret
