# rate_esp.py Benchmark for uasyncio. Author Peter Hinch April 2017.
# Benchmark uasyncio round-robin scheduling performance
# This measures the rate at which uasyncio can schedule a minimal coro which
# mereley increments a global.

# Test for ESP8266. Times below at 160/80MHz
# Outcome: minimal coros are scheduled at an interval of ~1.2/1.76ms with 'yield'
# 1.7/2.5ms with 'await asyncio.sleep_ms(0)'

import uasyncio as asyncio
from machine import freq
freq(80000000)

num_coros = (10,)
iterations = [0,]
duration = 10  # Time to run for each number of coros
count = 0
done = False

async def report():
    while not done:
        await asyncio.sleep(1)
    for x, n in enumerate(num_coros):
        print('Coros {:4d}  Iterations/sec {:5d}  Duration {:3d}us'.format(
            n, int(iterations[x]/duration), int(duration*1000000/iterations[x])))

async def foo():
    global count
    while True:
        yield
        count += 1

async def test():
    global count, done
    old_n = 0
    for n, n_coros in enumerate(num_coros):
        print('Testing {} coros for {}secs'.format(n_coros, duration))
        count = 0
        for _ in range(n_coros - old_n):
            loop.create_task(foo())
        old_n = n_coros
        await asyncio.sleep(duration)
        iterations[n] = count
    done = True

ntasks = max(num_coros) + 2
loop = asyncio.get_event_loop(ntasks, ntasks)
loop.create_task(test())
loop.run_until_complete(report())

