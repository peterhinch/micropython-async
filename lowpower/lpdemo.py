# lpdemo.py Demo/test program for MicroPython asyncio low power operation
# Author: Peter Hinch
# Copyright Peter Hinch 2018-2019 Released under the MIT license

import rtc_time_cfg
rtc_time_cfg.enabled = True

from pyb import LED, Pin
import aswitch
import uasyncio as asyncio
try:
    if asyncio.version[0] != 'fast_io':
        raise AttributeError
except AttributeError:
    raise OSError('This requires fast_io fork of uasyncio.')
from rtc_time import Latency

class Button(aswitch.Switch):
    def __init__(self, pin):
        super().__init__(pin)
        self.close_func(self._sw_close)
        self._flag = False

    def pressed(self):
        f = self._flag
        self._flag = False
        return f

    def _sw_close(self):
        self._flag = True

running = False
def start(loop, leds, tims):
    global running
    running = True
    coros = []
    # Demo: assume app requires higher speed (not true in this instance)
    Latency(50)
    # Here you might apply power to external hardware
    for x, led in enumerate(leds):  # Create a coroutine for each LED
        coros.append(toggle(led, tims[x]))
        loop.create_task(coros[-1])
    return coros

def stop(leds, coros):
    global running
    running = False
    while coros:
        asyncio.cancel(coros.pop())
    # Remove power from external hardware
    for led in leds:
        led.off()
    Latency(200)  # Slow down scheduler to conserve power

async def monitor(loop, button):
    leds = [LED(x) for x in (1, 2, 3)]  # Create list of LED's and times
    tims = [200, 700, 1200]
    coros = start(loop, leds, tims)
    while True:
        if button.pressed():
            if running:
                stop(leds, coros)
            else:
                coros = start(loop, leds, tims)
        await asyncio.sleep_ms(0)

async def toggle(objLED, time_ms):
    while True:
        await asyncio.sleep_ms(time_ms)
        objLED.toggle()

loop = asyncio.get_event_loop()
button = Button(Pin('X1', Pin.IN, Pin.PULL_UP))
loop.create_task(monitor(loop, button))
loop.run_forever()
