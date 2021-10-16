# syn_test.py
# Tests the monitoring synchronous code and of an async method.

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import time
from machine import Pin, UART, SPI
import monitor

# Define interface to use
monitor.set_device(UART(2, 1_000_000))  # UART must be 1MHz
# monitor.set_device(SPI(2, baudrate=5_000_000), Pin('X1', Pin.OUT))  # SPI suggest >= 1MHz


class Foo:
    def __init__(self):
        pass

    @monitor.asyn(1, 2)  # ident 1/2 high
    async def pause(self):
        self.wait1()  # ident 3 10ms pulse
        await asyncio.sleep_ms(100)
        with monitor.mon_call(4):  # ident 4 10ms pulse
            self.wait2()
        await asyncio.sleep_ms(100)
        # ident 1/2 low

    @monitor.sync(3)  # Decorator so ident not reserved
    def wait1(self):
        time.sleep_ms(10)

    def wait2(self):
        time.sleep_ms(10)

async def main():
    monitor.init()
    asyncio.create_task(monitor.hog_detect())  # Make 10ms waitx gaps visible
    foo1 = Foo()
    foo2 = Foo()
    trig = monitor.trigger(5)
    while True:
        trig()  # Mark start with pulse on ident 5
        # Create two instances of .pause separated by 50ms
        asyncio.create_task(foo1.pause())
        await asyncio.sleep_ms(50)
        await foo2.pause()
        await asyncio.sleep_ms(50)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
