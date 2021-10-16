# quick_test.py
# Tests the monitoring of deliberate CPU hgging.

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import time
from machine import Pin, UART, SPI
import monitor

# Define interface to use
monitor.set_device(UART(2, 1_000_000))  # UART must be 1MHz
# monitor.set_device(SPI(2, baudrate=5_000_000), Pin('X1', Pin.OUT))  # SPI suggest >= 1MHz

trig = monitor.trigger(4)

@monitor.asyn(1)
async def foo(t):
    await asyncio.sleep_ms(t)

@monitor.asyn(2)
async def hog():
    await asyncio.sleep(5)
    trig()  # Hog start
    time.sleep_ms(500)

@monitor.asyn(3)
async def bar(t):
    await asyncio.sleep_ms(t)

async def main():
    monitor.init()
    asyncio.create_task(monitor.hog_detect())
    asyncio.create_task(hog())  # Will hog for 500ms after 5 secs
    while True:
        asyncio.create_task(foo(100))
        await bar(150)
        await asyncio.sleep_ms(50)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
