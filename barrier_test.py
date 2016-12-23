# barrier_test.py Test/demo of the 'micro' Barrier class
# Author: Peter Hinch
# Copyright Peter Hinch 2016 Released under the MIT license

# CPython 3.5 compatibility
# (ignore RuntimeWarning: coroutine '_g' was never awaited)
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from asyn import Barrier

async def killer(duration):
    await asyncio.sleep(duration)

def callback(text):
    print(text)

barrier = Barrier(3, callback, ('Synch',))

async def report():
    for i in range(5):
        print('{} '.format(i), end='')
        await barrier.signal_and_wait()

loop = asyncio.get_event_loop()
loop.create_task(report())
loop.create_task(report())
loop.create_task(report())
loop.run_until_complete(killer(2))
loop.close()
