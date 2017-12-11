# asyntest.py Test/demo of the 'micro' Event, Barrier and Semaphore classes
# Test/demo of official Lock class
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license

# Tests:
# ack_test()
# event_test()
# barrier_test()
# semaphore_test()  Pass True to test BoundedSemaphore class
# cancel_test1()  Awaiting cancellable coros
# cancel_test2() Cancellable coros as tasks and using barrier to synchronise.
# cancel_test3() Cancellation of a coro which has terminated.
# Issue ctrl-D after running each test

# CPython 3.5 compatibility
# (ignore RuntimeWarning: coroutine '_g' was never awaited)
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
try:
    from uasyncio.synchro import Lock
except ImportError:
    from asyn import Lock

from asyn import Event, Semaphore, BoundedSemaphore, Barrier, NamedCoro, CancelError

def printexp(exp, runtime=0):
    print('Expected output:')
    print('\x1b[32m')
    print(exp)
    print('\x1b[39m')
    if runtime:
        print('Running (runtime = {}s):'.format(runtime))
    else:
        print('Running (runtime < 1s):')

# ************ Test Event class ************
# Demo use of acknowledge event

async def event_wait(event, ack_event, n):
    await event
    print('Eventwait {} got event with value {}'.format(n, event.value()))
    ack_event.set()

async def run_ack():
    loop = asyncio.get_event_loop()
    event = Event()
    ack1 = Event()
    ack2 = Event()
    count = 0
    while True:
        loop.create_task(event_wait(event, ack1, 1))
        loop.create_task(event_wait(event, ack2, 2))
        event.set(count)
        count += 1
        print('event was set')
        await ack1
        ack1.clear()
        print('Cleared ack1')
        await ack2
        ack2.clear()
        print('Cleared ack2')
        event.clear()
        print('Cleared event')
        await asyncio.sleep(1)

async def ack_coro(delay):
    await asyncio.sleep(delay)
    print("I've seen attack ships burn on the shoulder of Orion...")
    print("Time to die...")

def ack_test():
    printexp('''event was set
Eventwait 1 got event with value 0
Eventwait 2 got event with value 0
Cleared ack1
Cleared ack2
Cleared event
event was set
Eventwait 1 got event with value 1
Eventwait 2 got event with value 1

... text omitted ...

Eventwait 1 got event with value 9
Eventwait 2 got event with value 9
Cleared ack1
Cleared ack2
Cleared event
I've seen attack ships burn on the shoulder of Orion...
Time to die...
''', 10)
    loop = asyncio.get_event_loop()
    loop.create_task(run_ack())
    loop.run_until_complete(ack_coro(10))

# ************ Test Lock and Event classes ************

async def run_lock(n, lock):
    print('run_lock {} waiting for lock'.format(n))
    await lock.acquire()
    print('run_lock {} acquired lock'.format(n))
    await asyncio.sleep(1)  # Delay to demo other coros waiting for lock
    lock.release()
    print('run_lock {} released lock'.format(n))

async def eventset(event):
    print('Waiting 5 secs before setting event')
    await asyncio.sleep(5)
    event.set()
    print('event was set')

async def eventwait(event):
    print('waiting for event')
    await event
    print('got event')
    event.clear()

async def run_event_test(lp):
    print('Test Lock class')
    loop = asyncio.get_event_loop()
    lock = Lock()
    loop.create_task(run_lock(1, lock))
    loop.create_task(run_lock(2, lock))
    loop.create_task(run_lock(3, lock))
    print('Test Event class')
    event = Event(lp)
    print('got here')
    loop.create_task(eventset(event))
    print('gh1')
    await eventwait(event)  # run_event_test runs fast until this point
    print('Event status {}'.format('Incorrect' if event.is_set() else 'OK'))
    print('Tasks complete')

def event_test(lp=True):  # Option to use low priority scheduling
    printexp('''Test Lock class
Test Event class
got here
gh1
waiting for event
run_lock 1 waiting for lock
run_lock 2 waiting for lock
run_lock 3 waiting for lock
Waiting 5 secs before setting event
run_lock 1 acquired lock
run_lock 1 released lock
run_lock 2 acquired lock
run_lock 2 released lock
run_lock 3 acquired lock
run_lock 3 released lock
event was set
got event
Event status OK
Tasks complete
''', 5)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_event_test(lp))

# ************ Barrier test ************

async def killer(duration):
    await asyncio.sleep(duration)

def callback(text):
    print(text)

async def report(barrier):
    for i in range(5):
        print('{} '.format(i), end='')
        await barrier

def barrier_test():
    printexp('''0 0 0 Synch
1 1 1 Synch
2 2 2 Synch
3 3 3 Synch
4 4 4 Synch
''')
    barrier = Barrier(3, callback, ('Synch',))
    loop = asyncio.get_event_loop()
    for _ in range(3):
        loop.create_task(report(barrier))
    loop.run_until_complete(killer(2))
    loop.close()

# ************ Semaphore test ************

async def run_sema(n, sema, barrier):
    print('run_sema {} trying to access semaphore'.format(n))
    async with sema:
        print('run_sema {} acquired semaphore'.format(n))
        await asyncio.sleep(1)  # Delay to demo other coros waiting for sema
    print('run_sema {} has released semaphore'.format(n))
    await barrier

async def run_sema_test(bounded):
    num_coros = 5
    loop = asyncio.get_event_loop()
    barrier = Barrier(num_coros + 1)
    if bounded:
        semaphore = BoundedSemaphore(3)
    else:
        semaphore = Semaphore(3)
    for n in range(num_coros):
        loop.create_task(run_sema(n, semaphore, barrier))
    await barrier  # Quit when all coros complete
    try:
        semaphore.release()
    except ValueError:
        print('Bounded semaphore exception test OK')

def semaphore_test(bounded=False):
    if bounded:
        exp = '''run_sema 0 trying to access semaphore
run_sema 0 acquired semaphore
run_sema 1 trying to access semaphore
run_sema 1 acquired semaphore
run_sema 2 trying to access semaphore
run_sema 2 acquired semaphore
run_sema 3 trying to access semaphore
run_sema 4 trying to access semaphore
run_sema 3 acquired semaphore
run_sema 0 has released semaphore
run_sema 4 acquired semaphore
run_sema 1 has released semaphore
run_sema 2 has released semaphore
run_sema 3 has released semaphore
run_sema 4 has released semaphore
Bounded semaphore exception test OK

Exact sequence of acquisition may vary when 3 and 4 compete for semaphore.'''
    else:
        exp = '''run_sema 0 trying to access semaphore
run_sema 0 acquired semaphore
run_sema 1 trying to access semaphore
run_sema 1 acquired semaphore
run_sema 2 trying to access semaphore
run_sema 2 acquired semaphore
run_sema 3 trying to access semaphore
run_sema 4 trying to access semaphore
run_sema 3 acquired semaphore
run_sema 0 has released semaphore
run_sema 4 acquired semaphore
run_sema 1 has released semaphore
run_sema 2 has released semaphore
run_sema 3 has released semaphore
run_sema 4 has released semaphore

Exact sequence of acquisition may vary when 3 and 4 compete for semaphore.'''
    printexp(exp, 3)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_sema_test(bounded))

# ************ Cancellation tests ************
# cancel_test1()

async def foo(num):
    try:
        await asyncio.sleep(4)
        return num + 42
    except CancelError:
        print('foo was cancelled.')
        return -1

def kill(task_name):
    if NamedCoro.cancel(task_name):
        print(task_name, 'will be cancelled when next scheduled')
    else:
        print(task_name, 'was not cancellable.')

# Example of a task which cancels another
async def bar():
    await asyncio.sleep(1)
    kill('foo')
    kill('not_me')  # Will fail because not yet scheduled

async def run_cancel_test1():
    loop = asyncio.get_event_loop()
    loop.create_task(bar())
    res = await NamedCoro(foo(5), 'foo')
    print(res)
    res = await NamedCoro(foo(0), 'not_me')  # Runs to completion
    print(res)

def cancel_test1():
    printexp('''foo will be cancelled when next scheduled
not_me was not cancellable.
foo was cancelled.
-1
42
''', 8)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test1())

# cancel_test2()
# This test uses a barrier so that cancelling task pauses until cancelled tasks
# have actually terminated. Also tests the propagation of the thrown exception
# to the awaiting coro.

async def forever(n):
    print('Started forever() instance', n)
    while True:
        await asyncio.sleep(7 + n)
        print('Running instance', n)

# Cancellable coros must trap the CancelError. If a barrier is used, coro must
# pass it whether cancelled or terminates normally.
async def rats(barrier, n):
    try:
        await forever(n)
    except CancelError:
        print('Instance', n, 'was cancelled')
    finally:
        await barrier(nowait = True)

async def run_cancel_test2():
    barrier = Barrier(3)
    loop = asyncio.get_event_loop()
    loop.create_task(NamedCoro(rats(barrier, 1), 'rats_1').task)
    loop.create_task(NamedCoro(rats(barrier, 2), 'rats_2').task)
    print('Running two tasks')
    await asyncio.sleep(10)
    print('About to cancel tasks')
    NamedCoro.cancel('rats_1')  # These will stop when their wait is complete
    NamedCoro.cancel('rats_2')
    await barrier  # So wait for that to occur.
    print('tasks were cancelled')

def cancel_test2():
    printexp('''Running two tasks
Started forever() instance 1
Started forever() instance 2
Running instance 1
Running instance 2
About to cancel tasks
Instance 1 was cancelled
Instance 2 was cancelled
tasks were cancelled
''', 20)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test2())

# cancel_test2()
# Test of cancelling a task which has already terminated

# Cancellable coros must trap the CancelError
async def cant3(barrier):
    try:
        await asyncio.sleep(1)
        print('Task cant3 has ended.')
    except CancelError:
        print('Task cant3 was cancelled')
    finally:
        await barrier(nowait = True)

async def run_cancel_test3():
    barrier = Barrier(2)
    loop = asyncio.get_event_loop()
    loop.create_task(NamedCoro(cant3(barrier), 'cant3').task)
    print('Running task')
    await asyncio.sleep(3)
    print('About to cancel task')
    NamedCoro.cancel('cant3')
    print('Cancelled')
    await barrier
    print('tasks were cancelled')

def cancel_test3():
    printexp('''Running task
Task cant3 has ended.
About to cancel task
Cancelled
tasks were cancelled
''', 3)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test3())
