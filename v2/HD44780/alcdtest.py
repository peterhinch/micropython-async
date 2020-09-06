# alcdtest.py Test program for LCD class
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license
# runs for 20s
import uasyncio as asyncio
import utime as time
from alcd import LCD, PINLIST

lcd = LCD(PINLIST, cols = 16)

async def lcd_task():
    for secs in range(20, -1, -1):
        lcd[0] = 'MicroPython {}'.format(secs)
        lcd[1] = "{:11d}uS".format(time.ticks_us())
        await asyncio.sleep(1)


loop = asyncio.get_event_loop()
loop.run_until_complete(lcd_task())
