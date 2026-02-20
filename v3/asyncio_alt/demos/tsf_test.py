# tsf_test.py Test/demo for asyncio_alt

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2025 Peter Hinch

import asyncio_alt as asyncio

# import asyncio
import time
import io

MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

tsf = asyncio.ThreadSafeFlag()
tim = 0


async def block(n):
    while True:
        time.sleep_ms(5)
        # print('n', n)
        await asyncio.sleep_ms(0)


async def trigger(m):
    global tim
    for x in range(m):
        tim = time.ticks_ms()
        tsf.set()
        await asyncio.sleep_ms(100)  # Pause


async def wait():
    x = 0
    while True:
        await tsf.wait()
        print(f"Iteration: {x} Latency: {time.ticks_diff(time.ticks_ms(), tim)}ms")
        x += 1


s1 = """
This tests the latency of a ThreadSafeFlag in the presence of
multiple running tasks: first under normal roundrobin scheduling.
Ideal time is 0.
"""
s2 = """
Now using I/O priority scheduling.
"""


async def timer_test(m):
    print(s1)
    tasks = []
    for n in range(10):
        tasks.append(asyncio.create_task(block(n)))
    tw = asyncio.create_task(wait())
    await trigger(m)
    print(s2)
    asyncio.roundrobin(False)
    await trigger(m)
    tw.cancel()
    print("Done.")


asyncio.run(timer_test(10))
