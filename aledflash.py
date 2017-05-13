# aledflash.py Demo/test program for MicroPython asyncio
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license
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
    loop = asyncio.get_event_loop()
    duration = int(duration)
    if duration > 0:
        print("Flash LED's for {:3d} seconds".format(duration))
    leds = [pyb.LED(x) for x in range(1,5)]  # Initialise all four on board LED's
    for x, led in enumerate(leds):           # Create a coroutine for each LED
        t = int((0.2 + x/2) * 1000)
        loop.create_task(toggle(leds[x], t))
    loop.run_until_complete(killer(duration))
    loop.close()

test(10)
