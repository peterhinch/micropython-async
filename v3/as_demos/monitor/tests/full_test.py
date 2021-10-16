# full_test.py

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Tests monitoring of timeout, task cancellation and multiple instances.

import uasyncio as asyncio
from machine import Pin, UART, SPI
import monitor

trig = monitor.trigger(4)
# Define interface to use
monitor.set_device(UART(2, 1_000_000))  # UART must be 1MHz
#monitor.set_device(SPI(2, baudrate=5_000_000), Pin('X1', Pin.OUT))  # SPI suggest >= 1MHz

@monitor.asyn(1, 3)
async def forever():
    while True:
        await asyncio.sleep_ms(100)


async def main():
    monitor.init()
    asyncio.create_task(monitor.hog_detect())  # Watch for gc dropouts on ID0
    while True:
        trig()
        try:
            await asyncio.wait_for_ms(forever(), 100)  # 100ms pulse on ID1
        except asyncio.TimeoutError:  # Mandatory error trapping
            pass
        # Task has now timed out
        await asyncio.sleep_ms(100)
        tasks = []
        for _ in range(5):  # ID 1, 2, 3 go high, then 500ms pause
            tasks.append(asyncio.create_task(forever()))
            await asyncio.sleep_ms(100)
        while tasks:  # ID 3, 2, 1 go low
            tasks.pop().cancel()
            await asyncio.sleep_ms(100)
        await asyncio.sleep_ms(100)
        

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
