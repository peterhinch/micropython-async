# metrics.py Check on scheduling performance of an application
# Released under the MIT licence
# Copyright (c) Peter Hinch 2020

import uasyncio as asyncio
import gc
from utime import ticks_us, ticks_diff


def metrics():
    ncalls = 0
    max_d = 0
    min_d = 100_000_000
    tot_d = 0
    st = 'Max {}μs Min {}μs Avg {}μs No. of calls {} Freq {}'
    async def func():
        nonlocal ncalls, max_d, min_d, tot_d
        while True:
            tstart = ticks_us()
            t_last = None
            while ticks_diff(t := ticks_us(), tstart) < 10_000_000:
                await asyncio.sleep(0)
                if ncalls:
                    dt = ticks_diff(t, t_last)
                    max_d = max(max_d, dt)
                    min_d = min(min_d, dt)
                    tot_d += dt
                ncalls += 1
                t_last = t
            print(st.format(max_d, min_d, tot_d//ncalls, ncalls, ncalls//10))
            gc.collect()
            print('mem free', gc.mem_free())
            ncalls = 0
            max_d = 0
            min_d = 100_000_000
            tot_d = 0
    return func

# Example of call
async def main():
    asyncio.create_task(metrics()())  # Note the syntax
    while True:
        await asyncio.sleep(0)

#asyncio.run(main())
