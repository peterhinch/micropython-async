# aremote.py Decoder for NEC protocol IR remote control
# e.g.https://www.adafruit.com/products/389

# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license

# Supports Pyboard and ESP8266. Requires asyncio library. Runs a user callback
# when a button is pressed. Assumes a Vishay TSOP4838 receiver chip or
# https://www.adafruit.com/products/157 connected to an arbitrary pin.
# Protocol definition:
# http://techdocs.altium.com/display/FPGA/NEC+Infrared+Transmission+Protocol
# http://www.circuitvalley.com/2013/09/nec-protocol-ir-infrared-remote-control.html

# On ESP8266 transmission errors are common. This is because, even at 160MHz,
# the Pin interrupt latency can exceed the pulse width. Transmission errors can
# occur for reasons including r/c not aligned properly or nearly out of range.
# User feedback should be provided on success to encourage users to retry in
# event of failure.

# Use art.py to characterise a remote. art1.py is a simple test program.

from sys import platform
import uasyncio as asyncio
from asyn import Event
from micropython import alloc_emergency_exception_buf, const
from array import array
from utime import ticks_us, ticks_diff
if platform == 'pyboard':
    from pyb import Pin, ExtInt
else:
    from machine import Pin, freq

alloc_emergency_exception_buf(100)
# Repeat button code
REPEAT = -1
# Error codes
BADSTART = -2
BADBLOCK = -3
BADREP = -4
OVERRUN = -5
BADDATA = -6
BADADDR = -7

EDGECOUNT = const(68)  # No. of edges in data block


# On 1st edge start a block timer. When it times out decode the data. Time must
# exceed the worst case block transmission time, but (with asyncio latency) be
# less than the interval between a block start and a repeat code start (108ms)
# Value of 73 allows for up to 35ms latency.
class NEC_IR():
    block_time = 73 # 68.1ms nominal. Allow for some tx tolerance (?)
    def __init__(self, pin, callback, extended, *args):  # Optional args for callback
        self._ev_start = Event()
        self._callback = callback
        self._extended = extended
        self._args = args
        self._times = array('i',  (0 for _ in range(EDGECOUNT + 1)))  # +1 for overrun
        if platform == 'pyboard':
            ExtInt(pin, ExtInt.IRQ_RISING_FALLING, Pin.PULL_NONE, self._cb_pin)
        else:
            pin.irq(handler = self._cb_pin, trigger=(Pin.IRQ_FALLING | Pin.IRQ_RISING))
        self._edge = 0
        self._ev_start.clear()
        loop = asyncio.get_event_loop()
        loop.create_task(self._run())

    async def _run(self):
        loop = asyncio.get_event_loop()
        while True:
            await self._ev_start  # Wait until data collection has started
            # Compensate for asyncio latency
            latency = ticks_diff(loop.time(), self._ev_start.value())
            await asyncio.sleep_ms(self.block_time - latency)  # Data block should have ended
            self._decode()  # decode, clear event, prepare for new rx, call cb

    # Pin interrupt. Save time of each edge for later decode.
    def _cb_pin(self, line):
        # On overrun ignore pulses until software timer times out
        if self._edge <= EDGECOUNT:  # Allow 1 extra pulse to record overrun
            if not self._ev_start.is_set():  # First edge received
                loop = asyncio.get_event_loop()
                self._ev_start.set(loop.time())  # asyncio latency compensation
            self._times[self._edge] = ticks_us()
            self._edge += 1

    def _decode(self):
        overrun = self._edge > EDGECOUNT
        val = OVERRUN if overrun else BADSTART
        if not overrun:
            width = ticks_diff(self._times[1], self._times[0])
            if width > 4000:  # 9ms leading mark for all valid data
                width = ticks_diff(self._times[2], self._times[1])
                if width > 3000: # 4.5ms space for normal data
                    if self._edge < EDGECOUNT:
                        # Haven't received the correct number of edges
                        val = BADBLOCK
                    else:
                        # Time spaces only (marks are always 562.5µs)
                        # Space is 1.6875ms (1) or 562.5µs (0)
                        # Skip last bit which is always 1
                        val = 0
                        for edge in range(3, EDGECOUNT - 2, 2):
                            val >>= 1
                            if ticks_diff(self._times[edge + 1], self._times[edge]) > 1120:
                                val |= 0x80000000
                elif width > 1700: # 2.5ms space for a repeat code. Should have exactly 4 edges.
                    val = REPEAT if self._edge == 4 else BADREP
        addr = 0
        if val >= 0:  # validate. Byte layout of val ~cmd cmd ~addr addr
            addr = val & 0xff
            cmd = (val >> 16) & 0xff
            if addr == ((val >> 8) ^ 0xff) & 0xff:  # 8 bit address OK
                val = cmd if cmd == (val >> 24) ^ 0xff else BADDATA
            else:
                addr |= val & 0xff00  # pass assumed 16 bit address to callback
                if self._extended:
                    val = cmd if cmd == (val >> 24) ^ 0xff else BADDATA
                else:
                    val = BADADDR
        self._edge = 0  # Set up for new data burst and run user callback
        self._ev_start.clear()
        self._callback(val, addr, *self._args)
