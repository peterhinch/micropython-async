# quick_test.py

import uasyncio as asyncio
import time
from machine import Pin
from monitor import monitor, monitor_init, hog_detect, set_uart

set_uart(2)  # Define interface to use

@monitor(1)
async def foo(t, pin):
    pin(1)  # Measure latency
    pin(0)
    await asyncio.sleep_ms(t)

@monitor(2)
async def hog():
    await asyncio.sleep(5)
    time.sleep_ms(500)

@monitor(3)
async def bar(t):
    await asyncio.sleep_ms(t)


async def main():
    monitor_init()
    test_pin = Pin('X6', Pin.OUT)
    asyncio.create_task(hog_detect())
    asyncio.create_task(hog())  # Will hog for 500ms after 5 secs
    while True:
        asyncio.create_task(foo(100, test_pin))
        await bar(150)
        await asyncio.sleep_ms(50)

asyncio.run(main())
