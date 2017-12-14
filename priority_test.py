# priority_test.py
# Test/demo of task cancellation of low priority tasks
# Check availability of 'priority' version
try:
    import asyncio_priority as asyncio
    p_version = True
except ImportError:
    p_version = False

if not p_version:
    print('This program tests and therefore requires asyncio_priority.')

from asyn import Event, Semaphore, BoundedSemaphore, Barrier, NamedTask, StopTask

def printexp(exp, runtime=0):
    print('Expected output:')
    print('\x1b[32m')
    print(exp)
    print('\x1b[39m')
    if runtime:
        print('Running (runtime = {}s):'.format(runtime))
    else:
        print('Running (runtime < 1s):')

# cancel_test1()

async def foo(num):
    print('Starting foo', num)
    try:
        await asyncio.after(1)
        print('foo', num, 'ran to completion.')
    except StopTask:
        print('foo', num, 'was cancelled.')

def kill(task_name):
    if NamedTask.cancel(task_name):
        print(task_name, 'will be cancelled when next scheduled')
    else:
        print(task_name, 'was not cancellable.')

# Example of a task which cancels another
async def bar():
    await asyncio.sleep(1)
    kill('foo 0')  # Will fail because it has completed
    kill('foo 1')
    kill('foo 3')  # Will fail because not yet scheduled

async def run_cancel_test():
    loop = asyncio.get_event_loop()
    await NamedTask(foo(0), 'foo 0')
    loop.create_task(NamedTask(foo(1), 'foo 1').task)
    loop.create_task(bar())
    await asyncio.sleep(5)
    await NamedTask(foo(2), 'foo 2')
    await foo(5)
    loop.create_task(NamedTask(foo(3), 'foo 3').task)
    await asyncio.sleep(5)

def test():
    printexp('''Starting foo 0
foo 0 ran to completion.
Starting foo 1
foo 0 will be cancelled when next scheduled
foo 1 will be cancelled when next scheduled
foo 3 was not cancellable.
foo 1 was cancelled.
Starting foo 2
foo 2 ran to completion.
Starting foo 5
foo 5 ran to completion.
Starting foo 3
foo 3 ran to completion.
''', 14)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test())

test()
