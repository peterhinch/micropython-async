# Test/demo programs for Switch and Pushbutton classes
# Tested on Pyboard but should run on other microcontroller platforms
# running MicroPython with uasyncio library.

# Copyright (c) 2018-2022 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file
# Now executes .deinit()

# To run:
# from primitives.tests.switches import *
# test_sw()  # For example

from machine import Pin
from pyb import LED
from primitives import Switch, Pushbutton
import uasyncio as asyncio

helptext = '''
Test using switch or pushbutton between X1 and gnd.
Ground pin X2 to terminate test.

'''
tests = '''
\x1b[32m
Available tests:
test_sw Switch test.
test_swcb Switch with callback.
test_sw_event Switch with event.
test_btn Pushutton launching coros.
test_btncb Pushbutton launching callbacks.
btn_dynamic Change coros launched at runtime.
btn_event Pushbutton event interface.
\x1b[39m
'''
print(tests)

# Pulse an LED (coroutine)
async def pulse(led, ms):
    led.on()
    await asyncio.sleep_ms(ms)
    led.off()

# Pulse an LED when an event triggered
async def evt_pulse(event, led):
    while True:
        event.clear()
        await event.wait()
        led.on()
        await asyncio.sleep_ms(500)
        led.off()

# Toggle an LED (callback)
def toggle(led):
    led.toggle()

# Quit test by connecting X2 to ground
async def killer(obj):
    pin = Pin('X2', Pin.IN, Pin.PULL_UP)
    while pin.value():
        await asyncio.sleep_ms(50)
    obj.deinit()
    await asyncio.sleep_ms(0)

def run(obj):
    try:
        asyncio.run(killer(obj))
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        asyncio.new_event_loop()
        print(tests)


# Test for the Switch class passing coros
def test_sw():
    s = '''
close pulses green
open pulses red
'''
    print('Test of switch scheduling coroutines.')
    print(helptext)
    print(s)
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    sw = Switch(pin)
    # Register coros to launch on contact close and open
    sw.close_func(pulse, (green, 1000))
    sw.open_func(pulse, (red, 1000))
    run(sw)

# Test for the switch class with a callback
def test_swcb():
    s = '''
close toggles red
open toggles green
'''
    print('Test of switch executing callbacks.')
    print(helptext)
    print(s)
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    sw = Switch(pin)
    # Register a coro to launch on contact close
    sw.close_func(toggle, (red,))
    sw.open_func(toggle, (green,))
    run(sw)

# Test for the Switch class (events)
async def do_sw_event():
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    sw = Switch(pin)
    sw.open_func(None)
    sw.close_func(None)
    tasks = []
    for event, led in ((sw.close, 1), (sw.open, 2)):
        tasks.append(asyncio.create_task(evt_pulse(event, LED(led))))
    await killer(sw)
    for task in tasks:
        task.cancel()

def test_sw_event():
    s = '''
close pulse red
open pulses green
'''
    print('Test of switch triggering events.')
    print(helptext)
    print(s)
    try:
        asyncio.run(do_sw_event())
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        asyncio.new_event_loop()
        print(tests)

# Test for the Pushbutton class (coroutines)
# Pass True to test suppress
def test_btn(suppress=False, lf=True, df=True):
    s = '''
press pulses red
release pulses green
double click pulses yellow
long press pulses blue
'''
    print('Test of pushbutton scheduling coroutines.')
    print(helptext)
    print(s)
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    yellow = LED(3)
    blue = LED(4)
    pb = Pushbutton(pin, suppress)
    pb.press_func(pulse, (red, 1000))
    pb.release_func(pulse, (green, 1000))
    if df:
        print('Doubleclick enabled')
        pb.double_func(pulse, (yellow, 1000))
    if lf:
        print('Long press enabled')
        pb.long_func(pulse, (blue, 1000))
    run(pb)

# Test for the Pushbutton class (callbacks)
def test_btncb():
    s = '''
press toggles red
release toggles green
double click toggles yellow
long press toggles blue
'''
    print('Test of pushbutton executing callbacks.')
    print(helptext)
    print(s)
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
    run(pb)

# Test for the Pushbutton class where callback coros change dynamically
def setup(pb, press, release, dbl, lng, t=1000):
    s = '''
Functions are changed:
LED's pulse for 2 seconds
press pulses blue
release pulses red
double click pulses green
long pulses yellow
'''
    pb.press_func(pulse, (press, t))
    pb.release_func(pulse, (release, t))
    pb.double_func(pulse, (dbl, t))
    if lng is not None:
        pb.long_func(pulse, (lng, t))
        print(s)

def btn_dynamic():
    s = '''
press pulses red
release pulses green
double click pulses yellow
long press changes button functions.
'''
    print('Test of pushbutton scheduling coroutines.')
    print(helptext)
    print(s)
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    red = LED(1)
    green = LED(2)
    yellow = LED(3)
    blue = LED(4)
    pb = Pushbutton(pin)
    setup(pb, red, green, yellow, None)
    pb.long_func(setup, (pb, blue, red, green, yellow, 2000))
    run(pb)

# Test for the Pushbutton class (events)
async def do_btn_event():
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)
    pb = Pushbutton(pin)
    pb.press_func(None)
    pb.release_func(None)
    pb.double_func(None)
    pb.long_func(None)
    tasks = []
    for event, led in ((pb.press, 1), (pb.release, 2), (pb.double, 3), (pb.long, 4)):
        tasks.append(asyncio.create_task(evt_pulse(event, LED(led))))
    await killer(pb)
    for task in tasks:
        task.cancel()

def btn_event():
    s = '''
press pulse red
release pulses green
double click pulses yellow
long press pulses blue
'''
    print('Test of pushbutton triggering events.')
    print(helptext)
    print(s)
    try:
        asyncio.run(do_btn_event())
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        asyncio.new_event_loop()
        print(tests)

