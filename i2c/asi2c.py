# asi2c.py A communications link using I2C slave mode on Pyboard.

# The MIT License (MIT)
#
# Copyright (c) 2018 Peter Hinch
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import uasyncio as asyncio
import machine
import utime
from micropython import const
import io

_MP_STREAM_POLL_RD = const(1)
_MP_STREAM_POLL_WR = const(4)
_MP_STREAM_POLL = const(3)
_MP_STREAM_ERROR = const(-1)
# Delay compensates for short Responder interrupt latency. Must be >= max delay
# between Initiator setting a pin and initiating an I2C transfer: ensure
# Initiator sets up first.
_DELAY = const(20)  # μs

# Base class provides user interface and send/receive object buffers
class Channel(io.IOBase):
    def __init__(self, i2c, own, rem, verbose):
        self.verbose = verbose
        self.synchronised = False
        # Hardware
        self.i2c = i2c
        self.own = own
        self.rem = rem
        own.init(mode=machine.Pin.OUT, value=1)
        rem.init(mode=machine.Pin.IN, pull=machine.Pin.PULL_UP)
        # I/O
        self.txbyt = b''
        self.rxbyt = b''
        self.last_tx = 0  # Size of last buffer sent

    async def _sync(self):
        self.verbose and print('Synchronising')
        self.own(0)
        while self.rem():
            await asyncio.sleep_ms(100)
        # Both pins are now low
        await asyncio.sleep(0)
        self.verbose and print('Synchronised')
        self.synchronised = True

    def waitfor(self, val):  # Initiator overrides
        while not self.rem() == val:
            pass

    # Concatenate incoming bytes instance.
    def _handle_rxd(self, msg):
        self.rxbyt = b''.join((self.rxbyt, msg))

    # Get bytes if present. Return bytes, len as 2 bytes, len
    def _get_tx_data(self):
        d = self.txbyt
        n = len(d)
        return d, n.to_bytes(2, 'little'), n

    def _txdone(self):
        self.txbyt = b''

# Stream interface

    def ioctl(self, req, arg):
        ret = _MP_STREAM_ERROR
        if req == _MP_STREAM_POLL:
            ret = 0
            if self.synchronised:
                if arg & _MP_STREAM_POLL_RD:
                    if self.rxbyt:
                        ret |= _MP_STREAM_POLL_RD
                if arg & _MP_STREAM_POLL_WR:
                    if not self.txbyt:
                        ret |= _MP_STREAM_POLL_WR
        return ret

    def readline(self):
        n = self.rxbyt.find(b'\n')
        if n == -1:
            t = self.rxbyt[:]
            self.rxbyt = b''
        else:
            t = self.rxbyt[: n + 1]
            self.rxbyt = self.rxbyt[n + 1 :]
        return t.decode()

    def read(self, n):
        t = self.rxbyt[:n]
        self.rxbyt = self.rxbyt[n:]
        return t.decode()

    def write(self, buf, off, sz):
        if self.synchronised:
            if self.txbyt:  # Waiting for existing data to go out
                return 0
            d = buf[off : off + sz]
            self.txbyt = d
            return len(d)
        return 0

# User interface

    # Wait for sync
    async def ready(self):
        while not self.synchronised:
            await asyncio.sleep_ms(100)

    # Leave pin high in case we run again
    def close(self):
        self.own(1)

# Responder is I2C master. It is cross-platform and uses machine.
# It does not handle errors: if I2C fails it dies and awaits reset by initiator.
# send_recv is triggered by Interrupt from Initiator.

class Responder(Channel):
    addr = 0x12
    def __init__(self, i2c, pin, pinack, verbose=True):
        super().__init__(i2c, pinack, pin, verbose)
        loop = asyncio.get_event_loop()
        loop.create_task(self._run())

    async def _run(self):
        await self._sync()  # own pin ->0, wait for remote pin == 0
        self.rem.irq(handler = self._handler, trigger = machine.Pin.IRQ_RISING)

    # Request was received: immediately read payload size, then payload
    # On Pyboard blocks for 380μs to 1.2ms for small amounts of data
    def _handler(self, _, sn=bytearray(2)):
#        tstart = utime.ticks_us()  # TEST
        addr = Responder.addr
        self.rem.irq(handler = None, trigger = machine.Pin.IRQ_RISING)
        utime.sleep_us(_DELAY)  # Ensure Initiator has set up to write.
        self.i2c.readfrom_into(addr, sn)
        self.own(1)
        self.waitfor(0)
        self.own(0)
        n = int.from_bytes(sn, 'little')  # no of bytes to receive
        if n:
            self.waitfor(1)
            utime.sleep_us(_DELAY)
            data = self.i2c.readfrom(addr, n)
            self.own(1)
            self.waitfor(0)
            self.own(0)
            self._handle_rxd(data)

        s, nb, n = self._get_tx_data()
        self.own(1)  # Request to send
        self.waitfor(1)
        utime.sleep_us(_DELAY)
        self.i2c.writeto(addr, nb)
        self.own(0)
        self.waitfor(0)
        if n:
            self.own(1)
            self.waitfor(1)
            utime.sleep_us(_DELAY)
            self.i2c.writeto(addr, s)
            self.own(0)
            self.waitfor(0)
            self._txdone()  # Invalidate source
        self.rem.irq(handler = self._handler, trigger = machine.Pin.IRQ_RISING)
#        print('Time: ', utime.ticks_diff(utime.ticks_us(), tstart))
