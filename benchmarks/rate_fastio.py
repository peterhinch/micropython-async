# rate_fastio.py Benchmark for uasyncio. Author Peter Hinch July 2018.
# This version tests the fast_io version when I/O is not pending.
# Benchmark uasyncio round-robin scheduling performance
# This measures the rate at which uasyncio can schedule a minimal coro which
# mereley increments a global.

# This is identical to rate.py but instantiates io and lp queues
# Outcome: minimal coros are scheduled at an interval of ~206μs

import uasyncio as asyncio

num_coros = (100, 200, 500, 1000)
iterations = [0, 0, 0, 0]
duration = 2  # Time to run for each number of coros
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
loop = asyncio.get_event_loop(ntasks, ntasks, 6, 6)
loop.create_task(test())
loop.run_until_complete(report())

