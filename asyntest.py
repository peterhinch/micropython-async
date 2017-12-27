# asyntest.py Test/demo of the 'micro' Event, Barrier and Semaphore classes
# Test/demo of official asyncio library and official Lock class

# The MIT License (MIT)
#
# Copyright (c) 2017 Peter Hinch
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

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

from asyn import Event, Semaphore, BoundedSemaphore, Barrier, NamedTask, StopTask, Cancellable, sleep, cancellable

def print_tests():
    st = '''Available functions:
print_tests()  Print this list
ack_test()  Test event acknowledge
event_test(lp=True)  Test events. If lp use low priority mechanism
barrier_test()  Test the Barrier class
semaphore_test(bounded=False) Test Semaphore or BoundedSemaphore

cancel_test1()  Basic task cancellation
cancel_test2()  Use of Barrier to synchronise task cancellation
cancel_test3()  Test of cancellation of task which has already run to completion
cancel_test4()  Test of Cancellable class
cancel_test5()  Simple example of a cancellable task
Recommended to issue ctrl-D after running each test.
'''
    print(st)

print_tests()

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

async def foo(name, num):
    try:
        await asyncio.sleep(4)
        return num + 42
    except StopTask:
        print('foo was cancelled.')
        return -1
    finally:
        await NamedTask.end(name)

def kill(task_name):
    if NamedTask.cancel(task_name): 
        print(task_name, 'will be cancelled when next scheduled')
    else:
        print(task_name, 'was not cancellable.')

# Example of a task which cancels another
async def bar():
    await asyncio.sleep(1)
    kill('foo')
    kill('not me')  # Will fail because not yet scheduled

async def run_cancel_test1():
    loop = asyncio.get_event_loop()
    loop.create_task(bar())
    res = await NamedTask('foo', foo, 5)
    print(res, NamedTask.is_running('foo'))
    res = await NamedTask('not me', foo, 0)  # Runs to completion
    print(res, NamedTask.is_running('not me'))

def cancel_test1():
    printexp('''foo will be cancelled when next scheduled
not me was not cancellable.
foo was cancelled.
-1 False
42 False
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

# Cancellable coros must trap the StopTask. If a barrier is used, coro must
# pass it whether cancelled or terminates normally.
async def rats(name, n):
    try:
        await forever(n)
    except StopTask:
        print('Instance', n, 'was cancelled')
    finally:
        await NamedTask.end(name)

async def run_cancel_test2():
    barrier = Barrier(3)
    loop = asyncio.get_event_loop()
    loop.create_task(NamedTask('rats_1', rats, 1, barrier=barrier)())
    loop.create_task(NamedTask('rats_2', rats, 2, barrier=barrier)())
    print('Running two tasks')
    await asyncio.sleep(10)
    print('About to cancel tasks')
    NamedTask.cancel('rats_1')  # These will stop when their wait is complete
    NamedTask.cancel('rats_2')
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

# cancel_test3()
# Test of cancelling a task which has already terminated

# Cancellable coros must trap the StopTask
async def cant3(name):
    try:
        await asyncio.sleep(1)
        print('Task cant3 has ended.')
    except StopTask:
        print('Task cant3 was cancelled')
    finally:
        await NamedTask.end(name)

async def run_cancel_test3():
    barrier = Barrier(2)
    loop = asyncio.get_event_loop()
    loop.create_task(NamedTask('cant3', cant3, barrier=barrier)())
    print('Task cant3 running status', NamedTask.is_running('cant3'))
    await asyncio.sleep(3)
    print('Task cant3 running status', NamedTask.is_running('cant3'))
    print('About to cancel task')
    NamedTask.cancel('cant3')
    print('Cancelled')
    print('Task cant3 running status', NamedTask.is_running('cant3'))
    await barrier
    print('tasks were cancelled')

def cancel_test3():
    printexp('''Task cant3 running status True
Task cant3 has ended.
Task cant3 running status False
About to cancel task
Cancelled
Task cant3 running status False
tasks were cancelled
''', 3)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test3())

# cancel_test4()
# Test of cancelling a task which has already terminated

# Cancellable coros must trap the StopTask. They are passed the
# task_no automatically

@cancellable
async def cant40(task_no):
    while True:
        try:
            await sleep(1)
            print('Task cant40 no. {} running.'.format(task_no))
        except StopTask:
            print('Task cant40 no. {} was cancelled'.format(task_no))
            raise

@cancellable
async def cant41(task_no, arg=0):
    try:
        await sleep(1)
        print('Task cant41 no. {} running, arg {}.'.format(task_no, arg))
    except StopTask:
        print('Task cant41 no. {} was cancelled.'.format(task_no))
        raise
    else:
        print('Task cant41 no. {} ended.'.format(task_no))

async def cant42(task_no):
    while True:
        print('Task cant42 no. {} running'.format(task_no))
        await sleep(1.2)

# Test await syntax and throwing exception to subtask
@cancellable
async def chained(task_no):
    try:
        await cant42(task_no)
    except StopTask:
        print('Task chained no. {} was cancelled'.format(task_no))
        raise

async def run_cancel_test4():
    await Cancellable(cant41, 5)
    loop = asyncio.get_event_loop()
    loop.create_task(Cancellable(cant40)())  # 3 instances in default group 0
    loop.create_task(Cancellable(cant40)())
    loop.create_task(Cancellable(cant40)())
    loop.create_task(Cancellable(chained, group=1)())
    loop.create_task(Cancellable(cant41)())  # Runs to completion
    print('Running tasks')
    await asyncio.sleep(3)
    print('About to cancel group 0 tasks')
    await Cancellable.cancel_all()  # All in default group 0
    print('Group 0 tasks were cancelled')
    await asyncio.sleep(1)  # Demo chained still running
    print('About to cancel group 1 tasks')
    await Cancellable.cancel_all(1)  # Group 1
    print('Group 1 tasks were cancelled')
    await asyncio.sleep(1)

def cancel_test4():
    printexp('''Task cant41 no. 0 running, arg 5.
Task cant41 no. 0 ended.
Running tasks
Task cant42 no. 4 running
Task cant40 no. 1 running.
Task cant40 no. 2 running.
Task cant40 no. 3 running.
Task cant41 no. 5 running, arg 0.
Task cant41 no. 5 ended.
Task cant42 no. 4 running
Task cant40 no. 1 running.
Task cant40 no. 2 running.
Task cant40 no. 3 running.
Task cant42 no. 4 running
About to cancel group 0 tasks
Task cant40 no. 1 was cancelled
Task cant40 no. 2 was cancelled
Task cant40 no. 3 was cancelled
Group 0 tasks were cancelled
Task cant42 no. 4 running
About to cancel group 1 tasks
Task chained no. 4 was cancelled
Group 1 tasks were cancelled
''', 6)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test4())

# cancel_test5 A minimal example
@cancellable
async def cant50(task_no, num):
    while True:
        print(num)
        num += 1
        await sleep(1)

async def run_cancel_test5():
    loop = asyncio.get_event_loop()
    loop.create_task(Cancellable(cant50, 42)())
    await sleep(7.5)
    await Cancellable.cancel_all()
    print('Done')

def cancel_test5():
    printexp('''42
43
44
45
46
47
48
49
Done
''', 7.5)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test5())
