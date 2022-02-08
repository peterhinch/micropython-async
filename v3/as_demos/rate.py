# rate.py Benchmark for uasyncio. Author Peter Hinch Feb 2018-Apr 2020.
# Benchmark uasyncio round-robin scheduling performance
# This measures the rate at which uasyncio can schedule a minimal coro which
# mereley increments a global.

# Outcome on a Pyboard 1.1
# 100 minimal coros are scheduled at an interval of 195μs on uasyncio V3
# Compares with ~156μs on official uasyncio V2.

# Results for 100 coros on other platforms at standard clock rate:
# Pyboard D SF2W 124μs
# Pico 481μs
# ESP32 322μs
# ESP8266 1495μs (could not run 500 or 1000 coros)

# Note that ESP32 benchmarks are notoriously fickle. Above figure was for
# the reference board running MP V1.18. Results may vary with firmware
# depending on the layout of code in RAM/IRAM

import uasyncio as asyncio

num_coros = (100, 200, 500, 1000)
iterations = [0, 0, 0, 0]
duration = 2  # Time to run for each number of coros
count = 0
done = False

async def foo():
    global count
    while True:
        await asyncio.sleep_ms(0)
        count += 1

async def test():
    global count, done
    old_n = 0
    for n, n_coros in enumerate(num_coros):
        print('Testing {} coros for {}secs'.format(n_coros, duration))
        count = 0
        for _ in range(n_coros - old_n):
            asyncio.create_task(foo())
        old_n = n_coros
        await asyncio.sleep(duration)
        iterations[n] = count
    done = True

async def report():
    asyncio.create_task(test())
    while not done:
        await asyncio.sleep(1)
    for x, n in enumerate(num_coros):
        print('Coros {:4d}  Iterations/sec {:5d}  Duration {:3d}us'.format(
            n, int(iterations[x]/duration), int(duration*1000000/iterations[x])))

asyncio.run(report())
