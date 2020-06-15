# roundrobin.py Test/demo of round-robin scheduling
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license

# Result on Pyboard with print('Foo', n) commented out
# executions/second:
# Using yield: 4249
# Using sleep_ms(0) 2750
# Note using yield in a coro is "unofficial" and may not
# work in future uasyncio revisions.

import uasyncio as asyncio

count = 0
period = 5


async def foo(n):
    global count
    while True:
#        yield
        await asyncio.sleep_ms(0)
        count += 1
        print('Foo', n)


async def main(delay):
    print('Testing for {} seconds'.format(delay))
    await asyncio.sleep(delay)


loop = asyncio.get_event_loop()
loop.create_task(foo(1))
loop.create_task(foo(2))
loop.create_task(foo(3))
loop.run_until_complete(main(period))
print('Coro executions per sec =', count/period)
