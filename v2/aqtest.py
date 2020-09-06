# aqtest.py Demo/test program for MicroPython library micropython-uasyncio.queues
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license

import uasyncio as asyncio

from uasyncio.queues import Queue

q = Queue()

async def slow_process():
    await asyncio.sleep(2)
    return 42

async def bar():
    print('Waiting for slow process.')
    result = await slow_process()
    print('Putting result onto queue')
    await q.put(result)  # Put result on q

async def foo():
    print("Running foo()")
    result = await(q.get())
    print('Result was {}'.format(result))

async def main(delay):
    await asyncio.sleep(delay)
    print("I've seen starships burn off the shoulder of Orion...")
    print("Time to die...")

print('Test takes 3 secs')
loop = asyncio.get_event_loop()
loop.create_task(foo())
loop.create_task(bar())
loop.run_until_complete(main(3))
