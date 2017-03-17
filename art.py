# art.py Test program for IR remote control decoder aremote.py
# Supports NEC protocol IR remote control
# e.g.https://www.adafruit.com/products/389
# Supports Pyboard and ESP8266

# Author: Peter Hinch
# Copyright Peter Hinch 2016 Released under the MIT license

from sys import platform
import uasyncio as asyncio
if platform == 'pyboard':
    from pyb import Pin
elif platform == 'esp8266':
    from machine import Pin, freq
else:
    print('Unsupported platform', platform)

from aremote import *

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
    ir = NEC_IR(p, cb)
    loop = asyncio.get_event_loop()
    loop.run_forever()

test()
