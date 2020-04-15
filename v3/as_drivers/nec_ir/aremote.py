# aremote.py Decoder for NEC protocol IR remote control
# e.g.https://www.adafruit.com/products/389

# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license

from sys import platform
import uasyncio as asyncio
from asyn import Event
from micropython import const
from array import array
from utime import ticks_us, ticks_diff
if platform == 'pyboard':
    from pyb import Pin, ExtInt
else:
    from machine import Pin

ESP32 = platform == 'esp32' or platform == 'esp32_LoBo'

# Save RAM
# from micropython import alloc_emergency_exception_buf
# alloc_emergency_exception_buf(100)

# Result codes (accessible to application)
# Repeat button code
REPEAT = -1
# Error codes
BADSTART = -2
BADBLOCK = -3
BADREP = -4
OVERRUN = -5
BADDATA = -6
BADADDR = -7

_EDGECOUNT = const(68)  # No. of edges in data block


# On 1st edge start a block timer. When it times out decode the data. Time must
# exceed the worst case block transmission time, but (with asyncio latency) be
# less than the interval between a block start and a repeat code start (108ms)
# Value of 73 allows for up to 35ms latency.
class NEC_IR():
    def __init__(self, pin, callback, extended, *args):  # Optional args for callback
        self._ev_start = Event()
        self._callback = callback
        self._extended = extended
        self._addr = 0
        self.block_time = 80 if extended else 73  # Allow for some tx tolerance (?)
        self._args = args
        self._times = array('i',  (0 for _ in range(_EDGECOUNT + 1)))  # +1 for overrun
        if platform == 'pyboard':
            ExtInt(pin, ExtInt.IRQ_RISING_FALLING, Pin.PULL_NONE, self._cb_pin)
        elif ESP32:
            pin.irq(handler = self._cb_pin, trigger = (Pin.IRQ_FALLING | Pin.IRQ_RISING))
        else:
            pin.irq(handler = self._cb_pin, trigger = (Pin.IRQ_FALLING | Pin.IRQ_RISING), hard = True)
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
        t = ticks_us()
        # On overrun ignore pulses until software timer times out
        if self._edge <= _EDGECOUNT:  # Allow 1 extra pulse to record overrun
            if not self._ev_start.is_set():  # First edge received
                loop = asyncio.get_event_loop()
                self._ev_start.set(loop.time())  # asyncio latency compensation
            self._times[self._edge] = t
            self._edge += 1

    def _decode(self):
        overrun = self._edge > _EDGECOUNT
        val = OVERRUN if overrun else BADSTART
        if not overrun:
            width = ticks_diff(self._times[1], self._times[0])
            if width > 4000:  # 9ms leading mark for all valid data
                width = ticks_diff(self._times[2], self._times[1])
                if width > 3000: # 4.5ms space for normal data
                    if self._edge < _EDGECOUNT:
                        # Haven't received the correct number of edges
                        val = BADBLOCK
                    else:
                        # Time spaces only (marks are always 562.5µs)
                        # Space is 1.6875ms (1) or 562.5µs (0)
                        # Skip last bit which is always 1
                        val = 0
                        for edge in range(3, _EDGECOUNT - 2, 2):
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
                self._addr = addr
            else:
                addr |= val & 0xff00  # pass assumed 16 bit address to callback
                if self._extended:
                    val = cmd if cmd == (val >> 24) ^ 0xff else BADDATA
                    self._addr = addr
                else:
                    val = BADADDR
        if val == REPEAT:
            addr = self._addr  # Last valid addresss
        self._edge = 0  # Set up for new data burst and run user callback
        self._ev_start.clear()
        self._callback(val, addr, *self._args)
