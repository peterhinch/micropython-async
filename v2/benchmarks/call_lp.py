# call_lp.py Demo of low priority callback. Author Peter Hinch July 2018.
# Requires fast_io version of core.py

import pyb
import uasyncio as asyncio
try:
    if not(isinstance(asyncio.version, tuple)):
        raise AttributeError
except AttributeError:
    raise OSError('This program requires uasyncio fast_io version V0.24 or above.')

loop = asyncio.get_event_loop(lp_len=16)

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

def cb(arg):
    print(arg)

async def run_test():
    loop = asyncio.get_event_loop()
    loop.call_after(1, cb, 'One second has elapsed.')  # Test args
    loop.call_after_ms(500, cb, '500ms has elapsed.')
    print('Callbacks scheduled.')
    while True:
        loop.call_after(0, callback, pyb.rng())  # demo use of args
        yield 20  # 20ms

print('Test runs for 2 seconds')
loop = asyncio.get_event_loop()
loop.create_task(run_test())
loop.run_until_complete(report())

