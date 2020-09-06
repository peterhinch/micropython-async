# chain.py Demo of chained coros under MicroPython uasyncio
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

async def compute(x, y):
    print("Compute %s + %s ..." % (x, y))
    await asyncio.sleep(1.0)
    return x + y

async def print_sum(x, y):
    result = await compute(x, y)
    print("%s + %s = %s" % (x, y, result))

loop = asyncio.get_event_loop()
loop.run_until_complete(print_sum(1, 2))
loop.close()
