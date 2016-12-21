# Test/demo programs for the aswitch module.
# Tested on Pyboard but should run on other microcontroller platforms
# running MicroPython and uasyncio.
# Author: Peter Hinch.
# Copyright Peter Hinch 2016 Released under the MIT license.

from machine import Pin
from pyb import LED
from utime import ticks_add

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from aswitch import Switch, Pushbutton

# Pulse an LED (coroutine)
async def pulse(led, ms):
    led.on()
    await asyncio.sleep_ms(ms)
    led.off()

# Toggle an LED (callback)
def toggle(led):
    led.toggle()

# Quit test by connecting X2 to ground
async def killer():
    pin = Pin('X2', Pin.IN, Pin.PULL_UP)
    while pin.value():
        await asyncio.sleep_ms(50)

# Test for the Switch class passing coros
def test_sw():
    loop = asyncio.get_event_loop()
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    sw = Switch(pin)
    # Register a coro to launch on contact close
    sw.close_func(pulse, (green, 1000))
    sw.open_func(pulse, (red, 1000))
    loop.run_until_complete(killer())

# Test for the switch class with a callback
def test_swcb():
    loop = asyncio.get_event_loop()
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    sw = Switch(pin)
    # Register a coro to launch on contact close
    sw.close_func(toggle, (red,))
    sw.open_func(toggle, (green,))
    loop.run_until_complete(killer())

# Test for the Pushbutton class (coroutines)
def test_btn():
    loop = asyncio.get_event_loop()
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    yellow = LED(3)
    blue = LED(4)
    pb = Pushbutton(pin)
    pb.press_func(pulse, (red, 1000))
    pb.release_func(pulse, (green, 1000))
    pb.double_func(pulse, (yellow, 1000))
    pb.long_func(pulse, (blue, 1000))
    loop.run_until_complete(killer())

# Test for the Pushbutton class (callbacks)
def test_btncb():
    loop = asyncio.get_event_loop()
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    yellow = LED(3)
    blue = LED(4)
    pb = Pushbutton(pin)
    pb.press_func(toggle, (red,))
    pb.release_func(toggle, (green,))
    pb.double_func(toggle, (yellow,))
    pb.long_func(toggle, (blue,))
    loop.run_until_complete(killer())
