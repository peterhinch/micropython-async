# call_lp.py Demo of low priority callback. Author Peter Hinch April 2017.
# Requires experimental version of core.py

import uasyncio as asyncio
import pyb

# Determine version of core.py
low_priority = asyncio.low_priority if 'low_priority' in dir(asyncio) else None

count = 0
numbers = 0

async def report():
    yield 2000  # 2 secs
    print('Callback executed {} times. Expected count 2000/20 = 100 times.'.format(count))
    print('Avg. of {} random numbers in range 0 to 1023 was {}'.format(count, numbers // count))

def callback(num):
    global count, numbers
    count += 1
    numbers += num // 2**20  # range 0 to 1023

async def run_test():
    loop = asyncio.get_event_loop()
    while True:
        loop.call_lp(callback, pyb.rng())  # demo use of args
        yield 20  # 20ms

if low_priority is None:
    print('This demo requires the experimental version of core.py')
else:
    print('Test runs for 2 seconds')
    loop = asyncio.get_event_loop()
    loop.create_task(run_test())
    loop.run_until_complete(report())

