# Test of asyncio stream I/O using UART. For RP2.
# Author: Peter Hinch
# Copyright Peter Hinch 2017-2026 Released under the MIT license

# Link GPIO 0 and 1
# Run with no UART timeout: UART read never blocks.
import asyncio_alt as asyncio
from machine import UART, Pin

asyncio.power_mode(True)

uart = UART(0, 9600, rx=Pin(1, Pin.IN), tx=Pin(0, Pin.OUT), timeout=0)


async def sender():
    swriter = asyncio.StreamWriter(uart, {})
    while True:
        swriter.write("Hello uart\n")
        await swriter.drain()
        await asyncio.sleep(2)


async def receiver():
    sreader = asyncio.StreamReader(uart)
    while True:
        res = await sreader.readline()
        print("Received", res)
        await asyncio.sleep_ms(500)


async def main():
    asyncio.create_task(sender())
    asyncio.create_task(receiver())
    while True:
        await asyncio.sleep(1)


def test():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        asyncio.new_event_loop()
        print("as_demos.auart.test() to run again.")


test()
