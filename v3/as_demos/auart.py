# Test of uasyncio stream I/O using UART
# Author: Peter Hinch
# Copyright Peter Hinch 2017-2020 Released under the MIT license
# Link X1 and X2 to test.

import uasyncio as asyncio
from pyb import UART
uart = UART(4, 9600)

async def sender():
    swriter = asyncio.StreamWriter(uart, {})
    while True:
        await swriter.awrite('Hello uart\n')
        await asyncio.sleep(2)

async def receiver():
    sreader = asyncio.StreamReader(uart)
    while True:
        res = await sreader.readline()
        print('Recieved', res)

async def main():
    asyncio.create_task(sender())
    asyncio.create_task(receiver())
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
