# aremote_esp.py Variant of aremote.py for ESP8266
# Decoder for NEC protocol IR remote control e.g.https://www.adafruit.com/products/389
# asyncio version
# Assumes a Vishay TSOP4838 receiver chip or https://www.adafruit.com/products/157
# connected to an arbitrary pin
# http://techdocs.altium.com/display/FPGA/NEC+Infrared+Transmission+Protocol

from sys import platform
import uasyncio as asyncio
from asyn import Event
from micropython import alloc_emergency_exception_buf
from array import array
from utime import ticks_us, ticks_diff
if platform == 'pyboard':
    from pyb import Pin, ExtInt
else:
    from machine import Pin, freq

alloc_emergency_exception_buf(100)
REPEAT = -1
BADSTART = -2
BADBLOCK = -3
BADREP = -4
OVERRUN = -5
BADDATA = -6


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
        if platform == 'pyboard':
            ExtInt(pin, ExtInt.IRQ_RISING_FALLING, Pin.PULL_NONE, self._cb_pin)
        else:
            pin.irq(handler = self._cb_pin, trigger=(Pin.IRQ_FALLING | Pin.IRQ_RISING))
        self._reset()
        loop = asyncio.get_event_loop()
        loop.create_task(self._run())

    def _reset(self):
        self._edge = 0
        self._overrun = False
        self._ev_start.clear()

    async def _run(self):
        while True:
            await self._ev_start  # Wait until data collection has started
            await asyncio.sleep_ms(self.block_time)  # Data block should have ended
            self._decode() # decode, clear event, prepare for new rx, call cb

    # Pin interrupt. Save time of each edge for later decode.
    def _cb_pin(self, line):
        if not self._overrun: # Ignore pulses until software timer times out
            if not self._ev_start.is_set(): # First edge received
                loop = asyncio.get_event_loop()
                self._ev_start.set() #(loop.time()) # time for latency compensation
            self._times[self._edge] = ticks_us()
            if self._edge < self.edgecount:
                self._edge += 1
            else:
                self._overrun = True # Overrun. decode() will test and reset

    def _decode(self):
        val = OVERRUN if self._overrun else BADSTART
        if not self._overrun:
            width = ticks_diff(self._times[1], self._times[0])
            if width > 4000:  # 9ms leading mark for all valid data
                width = ticks_diff(self._times[2], self._times[1])
                if width > 3000: # 4.5ms space for normal data
                    if self._edge < self.edgecount:
                        val = BADBLOCK  # Haven't received the correct number of edges
                    else: # Time spaces only (marks are identical)
                        for edge_no in range(3, self.edgecount - 2, 2): # Last bit always 1 (short pulse)
                            val &= 0x1fffffff # Constrain to 32 bit integer (b30 == b31)
                            val <<= 1 # nos. will still be unique because of logical inverse address
                            width = ticks_diff(self._times[edge_no + 1], self._times[edge_no])
                            val |= width > 1120
                elif width > 1700: # 2.5ms space for a repeat code. Should have exactly 4 edges.
                    val = REPEAT if self._edge == 4 else BADREP
        addr = 0
        if val >= 0:  # validate
            addr = val >> 24
            if addr == ((val >> 16) ^ 0xff) & 0xff:  # Address OK
                cmd = (val >> 8) & 0xff
                val = cmd if cmd == (val & 0xff) ^ 0xff else BADDATA
            else:
                val = BADDATA
        self._reset()
        self._callback(val, addr)

# User callback. Buttons on the remote are characterised by address and data
# values. These are in range 0..255. If a button is held down a repeat code is
# transmitted. In this case data == REPEAT
# Applications typically ignore errors as they can be triggered by stray IR
# sources and can also occur if remote control is near limit of range. Users
# typically try again in the absence of a response.

errors = {BADSTART : 'Invalid start pulse', BADBLOCK : 'Error: bad block', BADREP : 'Error: repeat',
          OVERRUN : 'Error: overrun', BADDATA : 'Error: invalid data'}
def cb(data, addr):
    if data == REPEAT:
        print('Repeat')
    elif data >= 0:
        print(hex(data), hex(addr))
    else:
        print(errors[data])

def test():
    print('Test for IR receiver. Assumes NEC protocol.')
    if platform == 'pyboard':
        p = Pin('X3', Pin.IN)
    elif platform == 'esp8266':
        freq(160000000)
        p = Pin(13, Pin.IN)
    else:
        print('Unsupported platform')
        return
    ir = NEC_IR(p, cb)
    loop = asyncio.get_event_loop()
    loop.run_forever()

test()
