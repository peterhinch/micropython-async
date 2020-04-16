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
    except asyncio.CancelledError:
        print('Trapped foo timeout.')
        raise
    return n

async def bar(n):
    print('Start cancellable bar()')
    try:
        while True:
            await asyncio.sleep(1)
            n += 1
    except asyncio.CancelledError:  # Demo of trapping
        print('Trapped bar cancellation.')
        raise
    return n

async def do_cancel(task):
    await asyncio.sleep(5)
    print('About to cancel bar')
    task.cancel()

async def main(rex):
    bar_task = asyncio.create_task(bar(70))  # Note args here
    tasks = []
    tasks.append(barking(21))
    tasks.append(asyncio.wait_for(foo(10), 7))
    asyncio.create_task(do_cancel(bar_task))
    try:
        res = await asyncio.gather(*tasks, return_exceptions=rex)
    except asyncio.TimeoutError:
        print('foo timed out.')
        res = 'No result'
    print('Result: ', res)


exp_false = '''Test runs for 10s. Expected output:

Start cancellable bar()
Start normal coro barking()
Start timeout coro foo()
About to cancel bar
Trapped bar cancellation.
Done barking.
Trapped foo timeout.
foo timed out.
Result:  No result

'''
exp_true = '''Test runs for 10s. Expected output:

Start cancellable bar()
Start normal coro barking()
Start timeout coro foo()
About to cancel bar
Trapped bar cancellation.
Done barking.
Trapped foo timeout.
Result:  [42, TimeoutError()]

'''

def printexp(st):
    print('\x1b[32m')
    print(st)
    print('\x1b[39m')

def test(rex):
    st = exp_true if rex else exp_false
    printexp(st)
    try:
        asyncio.run(main(rex))
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        asyncio.new_event_loop()
        print()
        print('as_demos.gather.test() to run again.')
        print('as_demos.gather.test(True) to see effect of return_exceptions.')

test(rex=False)
