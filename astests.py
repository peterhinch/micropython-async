# TEST

from machine import Pin
from pyb import LED
from utime import ticks_add

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from aswitch import Switch, Pushbutton

# Pulse an LED
async def pulse(led, ms):
    led.on()
    await asyncio.sleep_ms(ms)
    led.off()

# Quit test by connecting X2 to ground
async def killer():
    pin = Pin('X2', Pin.IN, Pin.PULL_UP)
    while pin.value():
        await asyncio.sleep_ms(50)

# Test for the Switch class
def test_sw():
    loop = asyncio.get_event_loop()
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    sw = Switch(pin)
    # Register a coro to launch on contact close
    sw.close_coro(pulse, (green, 1000))
    sw.open_coro(pulse, (red, 1000))
    loop.run_until_complete(killer())

# Test for the Pushbutton class
def test_btn():
    loop = asyncio.get_event_loop()
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    yellow = LED(3)
    blue = LED(4)
    pb = Pushbutton(pin)
    pb.true_coro(pulse, (red, 1000))
    pb.false_coro(pulse, (green, 1000))
    pb.double_coro(pulse, (yellow, 1000))
    pb.long_coro(pulse, (blue, 1000))
    loop.run_until_complete(killer())
