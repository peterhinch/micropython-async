# art.py Test program for IR remote control decoder aremote.py
# Supports Pyboard and ESP8266

# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license

# Run this to characterise a remote.
# import as_drivers.nec_ir.art

from sys import platform
import uasyncio as asyncio
ESP32 = platform == 'esp32' or platform == 'esp32_LoBo'

if platform == 'pyboard':
    from pyb import Pin
elif platform == 'esp8266' or ESP32:
    from machine import Pin, freq
else:
    print('Unsupported platform', platform)

from .aremote import *

errors = {BADSTART : 'Invalid start pulse', BADBLOCK : 'Error: bad block',
          BADREP : 'Error: repeat', OVERRUN : 'Error: overrun',
          BADDATA : 'Error: invalid data', BADADDR : 'Error: invalid address'}

def cb(data, addr):
    if data == REPEAT:
        print('Repeat')
    elif data >= 0:
        print(hex(data), hex(addr))
    else:
        print('{} Address: {}'.format(errors[data], hex(addr)))

def test():
    print('Test for IR receiver. Assumes NEC protocol.')
    print('ctrl-c to stop.')
    if platform == 'pyboard':
        p = Pin('X3', Pin.IN)
    elif platform == 'esp8266':
        freq(160000000)
        p = Pin(13, Pin.IN)
    elif ESP32:
        p = Pin(23, Pin.IN)
    ir = NEC_IR(p, cb, True)  # Assume r/c uses extended addressing
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        asyncio.new_event_loop()  # Still need ctrl-d because of interrupt vector

test()
