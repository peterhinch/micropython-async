# call_lp.py Demo of low priority callback. Author Peter Hinch April 2017.
# Requires experimental version of core.py

import uasyncio as asyncio
import pyb

count = 0
numbers = 0

async def report():
    await asyncio.after(2)
    print('Callback executed {} times. Expected count 2000/20 = 100 times.'.format(count))
    print('Avg. of {} random numbers in range 0 to 1023 was {}'.format(count, numbers // count))

def callback(num):
    global count, numbers
    count += 1
    numbers += num // 2**20  # range 0 to 1023

def cb_1_sec():
    print('One second has elapsed.')

async def run_test():
    loop = asyncio.get_event_loop()
    loop.call_after(1, cb_1_sec)
    print('cb_1_sec scheduled')
    while True:
        loop.call_after(0, callback, pyb.rng())  # demo use of args
        yield 20  # 20ms

if not 'After' in dir(asyncio):
    print('This demo requires the experimental version of core.py')
else:
    print('Test runs for 2 seconds')
    loop = asyncio.get_event_loop()
    loop.create_task(run_test())
    loop.run_until_complete(report())

