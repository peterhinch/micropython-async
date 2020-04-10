# gather.py Demo of Gatherable coroutines. Includes 3 cases:
# 1. A normal coro
# 2. A coro with a timeout
# 3. A cancellable coro

import uasyncio as asyncio

async def barking(n):
    print('Start normal coro barking()')
    for _ in range(6):
        await asyncio.sleep(1)
    print('Done barking.')
    return 2 * n

async def foo(n):
    print('Start timeout coro foo()')
    try:
        while True:
            await asyncio.sleep(1)
            n += 1
    except Exception as e: #asyncio.TimeoutError:
        print('foo timeout.', e)
    return n

async def bar(n):
    print('Start cancellable bar()')
    try:
        while True:
            await asyncio.sleep(1)
            n += 1
    except Exception as e:
        print('bar stopped.', e)
    return n

async def do_cancel(task):
    await asyncio.sleep(5)
    print('About to cancel bar')
    task.cancel()

async def main():
    bar_task = asyncio.create_task(bar(70))  # Note args here
    tasks = []
    tasks.append(barking(21))
    tasks.append(asyncio.wait_for(foo(10), 7))
    asyncio.create_task(do_cancel(bar_task))
    res = await asyncio.gather(*tasks)
    print('Result: ', res)

asyncio.run(main())
