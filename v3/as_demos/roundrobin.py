# roundrobin.py Test/demo of round-robin scheduling
# Author: Peter Hinch
# Copyright Peter Hinch 2017-2020 Released under the MIT license

# Result on Pyboard 1.1 with print('Foo', n) commented out
# executions/second 5575.6 on uasyncio V3

# uasyncio V2 produced the following results
# 4249 - with a hack where sleep_ms(0) was replaced with yield
# Using sleep_ms(0) 2750

import uasyncio as asyncio

count = 0
period = 5


async def foo(n):
    global count
    while True:
        await asyncio.sleep_ms(0)
        count += 1
        print('Foo', n)


async def main(delay):
    for n in range(1, 4):
        asyncio.create_task(foo(n))
    print('Testing for {:d} seconds'.format(delay))
    await asyncio.sleep(delay)


asyncio.run(main(period))
print('Coro executions per sec =', count/period)
