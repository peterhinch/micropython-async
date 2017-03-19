# art1.py Test program for IR remote control decoder aremote.py
# Supports NEC protocol IR remote control
# e.g.https://www.adafruit.com/products/389
# Supports Pyboard and ESP8266

# Author: Peter Hinch
# Copyright Peter Hinch 2016 Released under the MIT license

# This uses a pair of buttons to turn an on-board LED on and off. Its aim is
# to enable you to decide if the reliability on the ESP8266 is adequate for
# your needs.

from sys import platform
import uasyncio as asyncio
if platform == 'pyboard':
    from pyb import Pin, LED
elif platform == 'esp8266':
    from machine import Pin, freq
else:
    print('Unsupported platform', platform)

from aremote import NEC_IR, REPEAT

# User callback. Buttons on the remote are characterised by address and data
# values. These are in range 0..255 (the remote under test does not use the
# extended address mode). If a button is held down a repeat code is
# transmitted. In this case data == REPEAT. data < REPEAT == error.

def cb(data, addr, led):
    if data == 1:  # Button 1. Adapt for your remote/buttons
        print('LED on')
        if platform == 'pyboard':
            led.on()
        else:
            led(0)
    elif data == 2:
        print('LED off')
        if platform == 'pyboard':
            led.off()
        else:
            led(1)
    elif data < REPEAT:
        print('Bad IR data')

def test():
    print('Test for IR receiver. Assumes NEC protocol. Turn LED on or off.')
    if platform == 'pyboard':
        p = Pin('X3', Pin.IN)
        led = LED(2)
    elif platform == 'esp8266':
        freq(160000000)
        p = Pin(13, Pin.IN)
        led = Pin(2, Pin.OUT)
        led(1)
    ir = NEC_IR(p, cb, True, led)  # Assume extended address mode r/c
    loop = asyncio.get_event_loop()
    loop.run_forever()

test()
