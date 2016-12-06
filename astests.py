# TEST

from machine import Pin
from pyb import LED
from utime import ticks_add

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from aswitch import Switch, Pushbutton

# Turn a LED off now
async def ledoff(led):
    yield
    led.off()

# Pulse an LED
async def pulse(loop, led, ms):
    led.on()
    loop.call_at(ticks_add(loop.time(), ms), ledoff(led))

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
    sw = Switch(loop, pin, pulse, (red, 1000), pulse, (green, 1000))
    loop.run_until_complete(killer())

# Test for the Pushbutton class
def test_btn():
    loop = asyncio.get_event_loop()
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    yellow = LED(3)
    blue = LED(4)
    sw = Pushbutton(loop, pin, true_func=pulse, true_func_args=(red, 1000),
                    false_func=pulse, false_func_args=(green, 1000),
                    double_func=pulse, double_func_args=(yellow, 1000),
                    long_func=pulse, long_func_args=(blue, 1000))
    loop.run_until_complete(killer())

#test_btn()
