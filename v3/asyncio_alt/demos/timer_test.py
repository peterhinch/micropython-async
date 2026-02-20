# timer_test.py Test/demo for asyncio_alt

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2025 Peter Hinch

import asyncio_alt as asyncio

# import asyncio
import time
import io

MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)


class MillisecTimer(io.IOBase):
    def __init__(self):
        self.end = 0
        self.sreader = asyncio.StreamReader(self)

    def __iter__(self):
        await self.sreader.read(1)

    def __call__(self, ms):
        self.end = time.ticks_add(time.ticks_ms(), ms)
        return self

    def read(self, _):
        return b"a"

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                if time.ticks_diff(time.ticks_ms(), self.end) >= 0:
                    ret |= MP_STREAM_POLL_RD
        return ret


timer = MillisecTimer()


async def block(n):
    while True:
        time.sleep_ms(5)
        # print('n', n)
        await asyncio.sleep_ms(0)


async def pause(m):
    for x in range(m):
        t = time.ticks_ms()
        await timer(100)  # Pause
        print(f"Iteration {x} {time.ticks_diff(time.ticks_ms(), t)}ms")


s1 = """
This tests the accuracy of a MillisecTimer instance in the presence of
multiple running tasks: first under normal roundrobin scheduling.
Ideal time is 100ms.
"""
s2 = """
Now using I/O priority scheduling.
"""


async def timer_test(m):
    print(s1)
    tasks = []
    for n in range(10):
        tasks.append(asyncio.create_task(block(n)))
    await pause(m)
    print(s2)
    asyncio.roundrobin(False)
    await pause(m)


asyncio.run(timer_test(10))
