# aqtest.py Demo/test program for MicroPython library micropython-uasyncio.queues
# Author: Peter Hinch
# Copyright Peter Hinch 2016 Released under the MIT license

import uasyncio as asyncio
from uasyncio.queues import Queue

q = Queue()

async def slow_process():
    await asyncio.sleep(1)
    return 42

async def bar():
    await slow_process()
    await q.put(42)  # Put result on q

async def foo():
    print("foo")
    result = await(q.get())
    print('Result was {}'.format(result))

async def main(delay):
    await asyncio.sleep(delay)
    print("I've seen starships burn off the shoulder of Orion...")
    print("Time to die...")

loop = asyncio.get_event_loop()
loop.create_task(foo())
loop.create_task(bar())
loop.run_until_complete(main(5))
