# aledflash.py Demo/test program for MicroPython asyncio
# Author: Peter Hinch
# Copyright Peter Hinch 2020 Released under the MIT license
# Flashes the onboard LED's each at a different rate. Stops after ten seconds.
# Run on MicroPython board bare hardware

import pyb
import uasyncio as asyncio

async def toggle(objLED, time_ms):
    while True:
        await asyncio.sleep_ms(time_ms)
        objLED.toggle()

# TEST FUNCTION

async def main(duration):
    print("Flash LED's for {} seconds".format(duration))
    leds = [pyb.LED(x) for x in range(1,4)]  # Initialise three on board LED's
    for x, led in enumerate(leds):  # Create a task for each LED
        t = int((0.2 + x/2) * 1000)
        asyncio.create_task(toggle(leds[x], t))
    await asyncio.sleep(duration)

def test(duration=10):
    try:
        asyncio.run(main(duration))
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        asyncio.new_event_loop()
        print('as_demos.aledflash.test() to run again.')

test()
