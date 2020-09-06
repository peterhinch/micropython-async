# syncom.py Synchronous communication channel between two MicroPython
# platforms. 4 June 2017
# Uses uasyncio.

# The MIT License (MIT)
#
# Copyright (c) 2017 Peter Hinch
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

# Timing: was 4.5mS per char between Pyboard and ESP8266 i.e. ~1.55Kbps. But
# this version didn't yield on every bit, invalidating t/o detection.
# New asyncio version yields on every bit.
# Instantaneous bit rate running ESP8266 at 160MHz: 1.6Kbps
# Mean throughput running test programs 8.8ms per char (800bps).

from utime import ticks_diff, ticks_ms
import uasyncio as asyncio
from micropython import const

_BITS_PER_CH = const(7)
_BITS_SYN = const(8)
_SYN = const(0x9d)
_RX_BUFLEN = const(100)

class SynComError(Exception):
    pass

class SynCom(object):
    def __init__(self, passive, ckin, ckout, din, dout, sig_reset=None,
                 timeout=0, string_mode=False, verbose=True):
        self.passive = passive
        self.string_mode = string_mode
        if not string_mode:
            global pickle
            import pickle
        self._running = False       # _run coro is down
        self._synchronised = False
        self.verbose = verbose
        self.idstr = 'passive' if self.passive else 'initiator'

        self.ckin = ckin            # Interface pins
        self.ckout = ckout
        self.din = din
        self.dout = dout
        self.sig_reset = sig_reset

        self._timeout = timeout     # In ms. 0 == No timeout.
        self.lsttx = []             # Queue of strings to send
        self.lstrx = []             # Queue of received strings

# Start interface and initiate an optional user task. If a timeout and reset
# signal are specified and the target times out, the target is reset and the
# interface restarted. If a user task is provided, this must return if a
# timeout occurs (i.e. not running() or await_obj returns None).
# If it returns for other (error) reasons, a timeout event is forced.
    async def start(self, user_task=None, awaitable=None):
        loop = asyncio.get_event_loop()
        while True:
            if not self._running:   # Restarting
                self.lstrx = []     # Clear down queues
                self.lsttx = []
                self._synchronised = False
                loop.create_task(self._run())  # Reset target (if possible)
                while not self._synchronised:  # Wait for sync
                    await asyncio.sleep_ms(100)
                if user_task is None:
                    while self._running:
                        await asyncio.sleep_ms(100)
                else:
                    await user_task(self)  # User task must quit on timeout
                    # If it quit for other reasons force a t/o exception
                    self.stop()
            await asyncio.sleep_ms(0)
            if awaitable is not None:  # User code may use an ExitGate
                await awaitable  # to ensure all coros have quit

# Can be used to force a failure
    def stop(self):
        self._running = False
        self.dout(0)
        self.ckout(0)

# Queue an object for tx. Convert to string NOW: snapshot of current
# object state
    def send(self, obj):
        if self.string_mode:
            self.lsttx.append(obj)  # strings are immutable
        else:
            self.lsttx.append(pickle.dumps(obj))

# Number of queued objects (None on timeout)
    def any(self):
        if self._running:
            return len(self.lstrx)

# Wait for an object. Return None on timeout.
# If in string mode returns a string (or None on t/o)
    async def await_obj(self, t_ms=10):
        while self._running:
            await asyncio.sleep_ms(t_ms)
            if len(self.lstrx):
                return self.lstrx.pop(0)

# running() is False if the target has timed out.
    def running(self):
        return self._running

# Private methods
    def _vbprint(self, *args):
        if self.verbose:
            print(*args)

    async def _run(self):
        self.indata = 0             # Current data bits
        self.inbits = 0
        self.odata = _SYN
        self.phase = 0              # Interface initial conditions
        if self.passive:
            self.dout(0)
            self.ckout(0)
        else:
            self.dout(self.odata & 1)
            self.ckout(1)
            self.odata >>= 1        # we've sent that bit
            self.phase = 1
        if self.sig_reset is not None:
            self._vbprint(self.idstr, ' resetting target...')
            self.sig_reset.on()
            await asyncio.sleep_ms(100)
            self.sig_reset.off()
            await asyncio.sleep(1)  # let target settle down

        self._vbprint(self.idstr, ' awaiting sync...')
        try:
            self._running = True    # False on failure: can be cleared by other tasks
            while self.indata != _SYN:  # Don't hog CPU while waiting for start
                await self._synchronise()
            self._synchronised = True
            self._vbprint(self.idstr, ' synchronised.')

            sendstr = ''            # string for transmission
            send_idx = None         # character index. None: no current string
            getstr = ''             # receive string
            rxbuf = bytearray(_RX_BUFLEN)
            rxidx = 0
            while True:
                if send_idx is None:
                    if len(self.lsttx):
                        sendstr = self.lsttx.pop(0)  # oldest first
                        send_idx = 0
                if send_idx is not None:
                    if send_idx < len(sendstr):
                        self.odata = ord(sendstr[send_idx])
                        send_idx += 1
                    else:
                        send_idx = None
                if send_idx is None:  # send zeros when nothing to send
                    self.odata = 0
                if self.passive:
                    await self._get_byte_passive()
                else:
                    await self._get_byte_active()
                if self.indata:  # Optimisation: buffer reduces allocations.
                    if rxidx >= _RX_BUFLEN:  # Buffer full: append to string.
                        getstr = ''.join((getstr, bytes(rxbuf).decode()))
                        rxidx = 0
                    rxbuf[rxidx] = self.indata
                    rxidx += 1
                elif rxidx or len(getstr):  # Got 0 but have data so string is complete.
                                            # Append buffer.
                    getstr = ''.join((getstr, bytes(rxbuf[:rxidx]).decode()))
                    if self.string_mode:
                        self.lstrx.append(getstr)
                    else:
                        try:
                            self.lstrx.append(pickle.loads(getstr))
                        except:     # Pickle fail means target has crashed
                            raise SynComError
                    getstr = ''  # Reset for next string
                    rxidx = 0

        except SynComError:
            if self._running:
                self._vbprint('SynCom Timeout.')
            else:
                self._vbprint('SynCom was stopped.')
        finally:
            self.stop()

    async def _get_byte_active(self):
        inbits = 0
        for _ in range(_BITS_PER_CH):
            inbits = await self._get_bit(inbits)  # LSB first
        self.indata = inbits

    async def _get_byte_passive(self):
        self.indata = await self._get_bit(self.inbits)  # MSB is outstanding
        inbits = 0
        for _ in range(_BITS_PER_CH - 1):
            inbits = await self._get_bit(inbits)
        self.inbits = inbits

    async def _synchronise(self):   # wait for clock
        t = ticks_ms()
        while self.ckin() == self.phase ^ self.passive ^ 1:
            # Other tasks can clear self._running by calling stop()
            if (self._timeout and ticks_diff(ticks_ms(), t) > self._timeout) or not self._running:
                raise SynComError
            await asyncio.sleep_ms(0)
        self.indata = (self.indata | (self.din() << _BITS_SYN)) >> 1
        odata = self.odata
        self.dout(odata & 1)
        self.odata = odata >> 1
        self.phase ^= 1
        self.ckout(self.phase)      # set clock

    async def _get_bit(self, dest):
        t = ticks_ms()
        while self.ckin() == self.phase ^ self.passive ^ 1:
            if (self._timeout and ticks_diff(ticks_ms(), t) > self._timeout) or not self._running:
                raise SynComError
            yield  # Faster than await asyncio.sleep_ms()
        dest = (dest | (self.din() << _BITS_PER_CH)) >> 1
        obyte = self.odata
        self.dout(obyte & 1)
        self.odata = obyte >> 1
        self.phase ^= 1
        self.ckout(self.phase)
        return dest
