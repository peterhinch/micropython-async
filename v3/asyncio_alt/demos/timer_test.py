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


async def block(n):
    while True:
        time.sleep_ms(5)
        # print('n', n)
        await asyncio.sleep_ms(0)


async def timer_test(m):
    timer = MillisecTimer()
    tasks = []
    for n in range(10):
        tasks.append(asyncio.create_task(block(n)))
    for x in range(m):
        t = time.ticks_ms()
        await timer(100)  # Pause
        print(x, time.ticks_diff(time.ticks_ms(), t))


asyncio.run(timer_test(20))
