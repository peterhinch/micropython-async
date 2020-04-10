# aledflash.py Demo/test program for MicroPython asyncio
# Author: Peter Hinch
# Copyright Peter Hinch 2020 Released under the MIT license
# Flashes the onboard LED's each at a different rate. Stops after ten seconds.
# Run on MicroPython board bare hardware

import pyb
import uasyncio as asyncio

async def killer(duration):
    await asyncio.sleep(duration)

async def toggle(objLED, time_ms):
    while True:
        await asyncio.sleep_ms(time_ms)
        objLED.toggle()

# TEST FUNCTION

def test(duration):
    duration = int(duration)
    if duration > 0:
        print("Flash LED's for {:3d} seconds".format(duration))
    leds = [pyb.LED(x) for x in range(1,4)]  # Initialise three on board LED's
    for x, led in enumerate(leds):           # Create a coroutine for each LED
        t = int((0.2 + x/2) * 1000)
        asyncio.create_task(toggle(leds[x], t))
    asyncio.run(killer(duration))

test(10)
