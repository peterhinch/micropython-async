# irq_event.py Interface between uasyncio and asynchronous events
# A thread-safe class. API is a subset of Event.

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import io

MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

class IRQ_EVENT(io.IOBase):
    def __init__(self):
        self.state = False  # False=unset; True=set
        self.sreader = asyncio.StreamReader(self)

    def wait(self):
        await self.sreader.read(1)
        self.state = False

    def set(self):
        self.state = True

    def is_set(self):
        return self.state

    def read(self, _):
        pass

    def clear(self):
        pass  # See docs

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                if self.state:
                    ret |= MP_STREAM_POLL_RD
        return ret
