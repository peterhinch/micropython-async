# syn_time.py
# Tests the monitoring synchronous code.
# Can run with run((1, monitor.WIDTH)) to check max width detection.

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import time
from machine import Pin, UART, SPI
import monitor

# Define interface to use
monitor.set_device(UART(2, 1_000_000))  # UART must be 1MHz
# monitor.set_device(SPI(2, baudrate=5_000_000), Pin('X1', Pin.OUT))  # SPI suggest >= 1MHz

trig0 = monitor.trigger(0)
twait = 20

async def test():
    while True:
        await asyncio.sleep_ms(100)
        trig0(True)
        await asyncio.sleep_ms(twait)
        trig0(False)

async def lengthen():
    global twait
    while twait < 200:
        twait += 1
        await asyncio.sleep(1)

async def main():
    monitor.init()
    asyncio.create_task(lengthen())
    await test()

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
