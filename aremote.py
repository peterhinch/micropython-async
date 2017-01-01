# aremote.py
# Decoder for NEC protocol IR remote control e.g.https://www.adafruit.com/products/389
# asyncio version
# Assumes a Vishay TSOP4838 receiver chip or https://www.adafruit.com/products/157
# connected to an arbitrary Pyboard pin
# http://techdocs.altium.com/display/FPGA/NEC+Infrared+Transmission+Protocol

import uasyncio as asyncio
from asyn import Event
import micropython
from array import array
from pyb import Pin, ExtInt
from utime import ticks_us, ticks_diff

micropython.alloc_emergency_exception_buf(100)

# On 1st edge start a block timer. When it times out decode the data. Time must
# exceed the worst case block transmission time, but (with asyncio latency) be
# less than the interval between a block start and a repeat code start (108ms)
# Value of 73 allows for up to 35ms latency.
class NEC_IR():
    edgecount = 68
    block_time = 73 # 68.1ms nominal. Allow for some tx tolerance (?)
    def __init__(self, pin, callback):
        self._ev_start = Event()
        self._callback = callback
        self._times = array('i',  (0 for _ in range(self.edgecount + 1))) # 1 for overrun
        ExtInt(pin, ExtInt.IRQ_RISING_FALLING, Pin.PULL_NONE, self._cb_pin)
        self._reset()
        loop = asyncio.get_event_loop()
        loop.create_task(self._run())

    def _reset(self):
        self._edge = 0
        self._in_block = False
        self._overrun = False
        self._ev_start.clear()

    async def _run(self):
        loop = asyncio.get_event_loop()
        block_time = self.block_time
        while True:
            await self._ev_start  # Wait unitl data collection has started
            delta = block_time - ticks_diff(loop.time(), self._ev_start.value())
            await asyncio.sleep_ms(delta)  # Data block should have ended
            self._decode() # decode, clear event, prepare for new rx, call cb

    # Pin interrupt. Save time of each edge for later decode.
    def _cb_pin(self, line):
        if self._overrun: # Ignore pulses until software timer times out
            return
        if not self._in_block: # First edge received
            loop = asyncio.get_event_loop()
            self._ev_start.set(loop.time()) # time for latency compensation
            self._in_block = True
        self._times[self._edge] = ticks_us()
        if self._edge < self.edgecount:
            self._edge += 1
        else:
            self._overrun = True # Overrun. decode() will test and reset

    def _decode(self):
        val = -3 if self._overrun else 0
        if not self._overrun:
            width = ticks_diff(self._times[1], self._times[0])
            if width > 4000:  # 9ms leading mark for all valid data
                width = ticks_diff(self._times[2], self._times[1])
                if width > 3000: # 4.5ms space for normal data
                    if self._edge < self.edgecount:
                        val = -1  # Haven't received the correct number of edges
                    else: # Time spaces only (marks are identical)
                        for edge_no in range(3, self.edgecount, 2):
                            val &= 0x1fffffff # Constrain to 32 bit integer (b30 == b31)
                            val <<= 1 # nos. will still be unique because of logical inverse address
                            width = ticks_diff(self._times[edge_no + 1], self._times[edge_no])
                            if width > 1120:
                                val += 1
                elif width > 1700: # 2.5ms space for a repeat code. Should have exactly 4 edges.
                    val = 1 if self._edge == 4 else -2
        self._reset()
        self._callback(val)


def cb(v):
    if v == 1:
        print('Repeat')
    elif v > 0:
        print(hex(v))
    elif v == -1:
        print('Error: bad block')
    elif v == -2:
        print('Error: repeat')
    elif v == -3:
        print('Error: overrun')

def test():
    print('Test for IR receiver. Assumes NEC protocol.')
    p = Pin('X3', Pin.IN)
    ir = NEC_IR(p, cb)
    loop = asyncio.get_event_loop()
    loop.run_forever()

test()
