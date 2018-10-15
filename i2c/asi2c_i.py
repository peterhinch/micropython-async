# asi2c_i.py A communications link using I2C slave mode on Pyboard.
# Initiator class

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
import gc
from asi2c import Channel

# The initiator is an I2C slave. It runs on a Pyboard. I2C uses pyb for slave
# mode, but pins are instantiated using machine.
# reset (if provided) is a means of resetting Responder in case of error: it
# is (pin, active_level, ms)
class Initiator(Channel):
    timeout = 1000  # ms Timeout to detect slave down
    t_poll = 100  # ms between Initiator polling Responder

    def __init__(self, i2c, pin, pinack, reset=None, verbose=True):
        super().__init__(i2c, pin, pinack, verbose)
        self.reset = reset
        if reset is not None:
            reset[0].init(mode=machine.Pin.OUT, value = not(reset[1]))
        # Self measurement
        self.nboots = 0  # No. of reboots of Responder
        self.block_max = 0  # Blocking times: max
        self.block_sum = 0  # Total
        self.block_cnt = 0  # Count
        loop = asyncio.get_event_loop()
        loop.create_task(self._run())

    def waitfor(self, val):
        to = Initiator.timeout
        tim = utime.ticks_ms()
        while not self.rem() == val:
            if utime.ticks_diff(utime.ticks_ms(), tim) > to:
                raise OSError

    async def reboot(self):
        if self.reset is not None:
            rspin, rsval, rstim = self.reset
            self.verbose and print('Resetting target.')
            rspin(rsval)  # Pulse reset line
            await asyncio.sleep_ms(rstim)
            rspin(not rsval)

    async def _run(self):
        while True:
            # If hardware link exists reboot Responder
            await self.reboot()
            self.txbyt = b''
            self.rxbyt = b''
            await self._sync()
            await asyncio.sleep(1)  # Ensure Responder is ready
            while True:
                gc.collect()
                try:
                    tstart = utime.ticks_us()
                    self._sendrx()
                    t = utime.ticks_diff(utime.ticks_us(), tstart)
                except OSError:
                    break
                await asyncio.sleep_ms(Initiator.t_poll)
                self.block_max = max(self.block_max, t)  # self measurement
                self.block_cnt += 1
                self.block_sum += t
            self.nboots += 1
            if self.reset is None:  # No means of recovery
                raise OSError('Responder fail.')

    # Send payload length (may be 0) then payload (if any)
    def _sendrx(self, sn=bytearray(2)):
        to = Initiator.timeout
        s, nb, n = self._get_tx_data()
        self.own(1)  # Triggers interrupt on responder
        self.i2c.send(nb, timeout=to)  # Must start before RX begins, but blocks until then
        self.waitfor(1)
        self.own(0)
        self.waitfor(0)
        if n:
            # start timer: timer CB sets self.own which causes RX
            self.own(1)
            self.i2c.send(s, timeout=to)
            self.waitfor(1)
            self.own(0)
            self.waitfor(0)
            self._txdone()  # Invalidate source
        # Send complete
        self.waitfor(1)  # Wait for responder to request send
        self.own(1)  # Acknowledge
        self.i2c.recv(sn, timeout=to)
        self.waitfor(0)
        self.own(0)
        n = int.from_bytes(sn, 'little')  # no of bytes to receive
        if n:
            self.waitfor(1)  # Wait for responder to request send
            self.own(1)  # Acknowledge
            data = self.i2c.recv(n, timeout=to)
            self.waitfor(0)
            self.own(0)
            self._handle_rxd(data)
