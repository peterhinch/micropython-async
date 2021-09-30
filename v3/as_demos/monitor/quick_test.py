# quick_test.py

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import time
from machine import Pin, UART, SPI
from monitor import monitor, monitor_init, hog_detect, set_device

# Define interface to use
set_device(UART(2, 1_000_000))  # UART must be 1MHz
#set_device(SPI(2, baudrate=5_000_000), Pin('X1', Pin.OUT))  # SPI suggest >= 1MHz

@monitor(1)
async def foo(t, pin):
    pin(1)  # Measure latency
    pin(0)
    await asyncio.sleep_ms(t)

@monitor(2)
async def hog():
    while True:
        await asyncio.sleep(5)
        time.sleep_ms(500)

@monitor(3)
async def bar(t):
    await asyncio.sleep_ms(t)


async def main():
    monitor_init()
    # test_pin = Pin('X6', Pin.OUT)
    test_pin = lambda _ : None  # If you don't want to measure latency
    asyncio.create_task(hog_detect())
    asyncio.create_task(hog())  # Will hog for 500ms after 5 secs
    while True:
        asyncio.create_task(foo(100, test_pin))
        await bar(150)
        await asyncio.sleep_ms(50)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
