# fast_can_test.py Test of cancellation of tasks which call sleep

# Copyright (c) Peter Hinch 2019
# Released under the MIT licence

import uasyncio as asyncio
import sys
ermsg = 'This test requires the fast_io version of uasyncio V2.4 or later.'
try:
    print('Uasyncio version', asyncio.version)
    if not isinstance(asyncio.version, tuple):
        print(ermsg)
        sys.exit(0)
except AttributeError:
    print(ermsg)
    sys.exit(0)

# If a task times out the TimeoutError can't be trapped:
# no exception is thrown to the task

async def foo(t):
    try:
        print('foo started')
        await asyncio.sleep(t)
        print('foo ended', t)
    except asyncio.CancelledError:
        print('foo cancelled', t)

async def lpfoo(t):
    try:
        print('lpfoo started')
        await asyncio.after(t)
        print('lpfoo ended', t)
    except asyncio.CancelledError:
        print('lpfoo cancelled', t)

async def run(coro, t):
    await asyncio.wait_for(coro, t)

async def bar(loop):
    foo1 = foo(1)
    foo5 = foo(5)
    lpfoo1 = lpfoo(1)
    lpfoo5 = lpfoo(5)
    loop.create_task(foo1)
    loop.create_task(foo5)
    loop.create_task(lpfoo1)
    loop.create_task(lpfoo5)
    await asyncio.sleep(2)
    print('Cancelling tasks')
    asyncio.cancel(foo1)
    asyncio.cancel(foo5)
    asyncio.cancel(lpfoo1)
    asyncio.cancel(lpfoo5)
    await asyncio.sleep(0)  # Allow cancellation to occur
    print('Pausing 7s to ensure no task still running.')
    await asyncio.sleep(7)
    print('Launching tasks with 2s timeout')
    loop.create_task(run(foo(1), 2))
    loop.create_task(run(lpfoo(1), 2))
    loop.create_task(run(foo(20), 2))
    loop.create_task(run(lpfoo(20), 2))
    print('Pausing 7s to ensure no task still running.')
    await asyncio.sleep(7)

loop = asyncio.get_event_loop(ioq_len=16, lp_len=16)
loop.run_until_complete(bar(loop))
