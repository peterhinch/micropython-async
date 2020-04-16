# art1.py Test program for IR remote control decoder aremote.py
# Supports Pyboard and ESP8266

# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license

# This uses a pair of buttons to turn an on-board LED on and off. Its aim is
# to enable you to decide if the reliability on the ESP8266 is adequate for
# your needs.

from sys import platform
import uasyncio as asyncio
ESP32 = platform == 'esp32' or platform == 'esp32_LoBo'
if platform == 'pyboard':
    from pyb import Pin, LED
elif platform == 'esp8266' or ESP32:
    from machine import Pin, freq
else:
    print('Unsupported platform', platform)

from aremote import NEC_IR, REPEAT

def cb(data, addr, led):
    if addr == 0x40:  # Adapt for your remote
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
    else:
        print('Incorrect remote')

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
    elif ESP32:
        p = Pin(23, Pin.IN)
        led = Pin(21, Pin.OUT)  # LED with 220Ω series resistor between 3.3V and pin 21
        led(1)
    ir = NEC_IR(p, cb, True, led)  # Assume extended address mode r/c
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        asyncio.new_event_loop()  # Still need ctrl-d because of interrupt vector

test()
