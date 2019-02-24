# priority_test.py
# Test/demo of task cancellation of low priority tasks
# Author: Peter Hinch
# Copyright Peter Hinch 2018 Released under the MIT license

# Check availability of 'priority' version
import uasyncio as asyncio
try:
    if not(isinstance(asyncio.version, tuple)):
        raise AttributeError
except AttributeError:
    raise OSError('This program requires uasyncio fast_io version V0.24 or above.')

loop = asyncio.get_event_loop(lp_len=16)
import asyn

def printexp(exp, runtime=0):
    print('Expected output:')
    print('\x1b[32m')
    print(exp)
    print('\x1b[39m')
    if runtime:
        print('Running (runtime = {}s):'.format(runtime))
    else:
        print('Running (runtime < 1s):')

@asyn.cancellable
async def foo(num):
    print('Starting foo', num)
    try:
        await asyncio.after(1)
        print('foo', num, 'ran to completion.')
    except asyn.StopTask:
        print('foo', num, 'was cancelled.')

async def kill(task_name):
    if await asyn.NamedTask.cancel(task_name):
        print(task_name, 'will be cancelled when next scheduled')
    else:
        print(task_name, 'was not cancellable.')

# Example of a task which cancels another
async def bar():
    await asyncio.sleep(1)
    await kill('foo 0')  # Will fail because it has completed
    await kill('foo 1')
    await kill('foo 3')  # Will fail because not yet scheduled

async def run_cancel_test():
    loop = asyncio.get_event_loop()
    await asyn.NamedTask('foo 0', foo, 0)
    loop.create_task(asyn.NamedTask('foo 1', foo, 1)())
    loop.create_task(bar())
    await asyncio.sleep(5)
    await asyn.NamedTask('foo 2', foo, 2)
    await asyn.NamedTask('foo 4', foo, 4)
    loop.create_task(asyn.NamedTask('foo 3', foo, 3)())
    await asyncio.sleep(5)

def test():
    printexp('''Starting foo 0
foo 0 ran to completion.
Starting foo 1
foo 0 was not cancellable.
foo 1 will be cancelled when next scheduled
foo 3 was not cancellable.
foo 1 was cancelled.
Starting foo 2
foo 2 ran to completion.
Starting foo 4
foo 4 ran to completion.
Starting foo 3
foo 3 ran to completion.
''', 14)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test())

test()
