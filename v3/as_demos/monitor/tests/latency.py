# latency.py
# Measure the time between a task starting and the Pico pin going high.
# Also the delay before a trigger occurs.

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
from machine import Pin, UART, SPI
import monitor

# Pin on host: modify for other platforms
test_pin = Pin('X6', Pin.OUT)
trig = monitor.trigger(2)

# Define interface to use
monitor.set_device(UART(2, 1_000_000))  # UART must be 1MHz
#monitor.set_device(SPI(2, baudrate=5_000_000), Pin('X1', Pin.OUT))  # SPI suggest >= 1MHz

@monitor.asyn(1)
async def pulse(pin):
    pin(1)  # Pulse pin
    pin(0)
    trig()  # Pulse Pico pin ident 2
    await asyncio.sleep_ms(30)

async def main():
    monitor.init()
    while True:
        await pulse(test_pin)
        await asyncio.sleep_ms(100)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
