# asyntest.py Test/demo of the 'micro' Event, Barrier and Semaphore classes
# Test/demo of official asyncio library and official Lock class

# The MIT License (MIT)
#
# Copyright (c) 2017-2018 Peter Hinch
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

import asyn

def print_tests():
    st = '''Available functions:
print_tests()  Print this list.
ack_test()  Test event acknowledge.
event_test()  Test Event and Lock objects.
barrier_test()  Test the Barrier class.
semaphore_test(bounded=False)  Test Semaphore or BoundedSemaphore.
condition_test(new=False)  Test the Condition class. Set arg True for new uasyncio.
gather_test()  Test the  Gather class

Recommended to issue ctrl-D after running each test.
'''
    print('\x1b[32m')
    print(st)
    print('\x1b[39m')

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
    event = asyn.Event()
    ack1 = asyn.Event()
    ack2 = asyn.Event()
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

async def run_event_test():
    print('Test Lock class')
    loop = asyncio.get_event_loop()
    lock = asyn.Lock()
    loop.create_task(run_lock(1, lock))
    loop.create_task(run_lock(2, lock))
    loop.create_task(run_lock(3, lock))
    print('Test Event class')
    event = asyn.Event()
    loop.create_task(eventset(event))
    await eventwait(event)  # run_event_test runs fast until this point
    print('Event status {}'.format('Incorrect' if event.is_set() else 'OK'))
    print('Tasks complete')

def event_test():
    printexp('''Test Lock class
Test Event class
waiting for event
run_lock 1 waiting for lock
run_lock 1 acquired lock
run_lock 2 waiting for lock
run_lock 3 waiting for lock
Waiting 5 secs before setting event
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
    loop.run_until_complete(run_event_test())

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
    barrier = asyn.Barrier(3, callback, ('Synch',))
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
        # Delay demonstrates other coros waiting for semaphore
        await asyncio.sleep(1 + n/10)  # n/10 ensures deterministic printout
    print('run_sema {} has released semaphore'.format(n))
    barrier.trigger()

async def run_sema_test(bounded):
    num_coros = 5
    loop = asyncio.get_event_loop()
    barrier = asyn.Barrier(num_coros + 1)
    if bounded:
        semaphore = asyn.BoundedSemaphore(3)
    else:
        semaphore = asyn.Semaphore(3)
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
run_sema 0 has released semaphore
run_sema 4 acquired semaphore
run_sema 1 has released semaphore
run_sema 3 acquired semaphore
run_sema 2 has released semaphore
run_sema 4 has released semaphore
run_sema 3 has released semaphore
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
run_sema 0 has released semaphore
run_sema 3 acquired semaphore
run_sema 1 has released semaphore
run_sema 4 acquired semaphore
run_sema 2 has released semaphore
run_sema 3 has released semaphore
run_sema 4 has released semaphore

Exact sequence of acquisition may vary when 3 and 4 compete for semaphore.'''
    printexp(exp, 3)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_sema_test(bounded))

# ************ Condition test ************

cond = asyn.Condition()
tim = 0

@asyn.cancellable
async def cond01():
    while True:
        await asyncio.sleep(2)
        with await cond:
            cond.notify(2)  # Notify 2 tasks

@asyn.cancellable
async def cond03():  # Maintain a count of seconds
    global tim
    await asyncio.sleep(0.5)
    while True:
        await asyncio.sleep(1)
        tim += 1

async def cond01_new():
    while True:
        await asyncio.sleep(2)
        with await cond:
            cond.notify(2)  # Notify 2 tasks

async def cond03_new():  # Maintain a count of seconds
    global tim
    await asyncio.sleep(0.5)
    while True:
        await asyncio.sleep(1)
        tim += 1

async def cond02(n, barrier):
    with await cond:
        print('cond02', n, 'Awaiting notification.')
        await cond.wait()
        print('cond02', n, 'triggered. tim =', tim)
        barrier.trigger()

def predicate():
    return tim >= 8 # 12

async def cond04(n, barrier):
    with await cond:
        print('cond04', n, 'Awaiting notification and predicate.')
        await cond.wait_for(predicate)
        print('cond04', n, 'triggered. tim =', tim)
        barrier.trigger()

async def cond_go(loop, new):
    ntasks = 7
    barrier = asyn.Barrier(ntasks + 1)
    if new:
        t1 = asyncio.create_task(cond01_new())
        t3 = asyncio.create_task(cond03_new())
    else:
        loop.create_task(asyn.Cancellable(cond01)())
        loop.create_task(asyn.Cancellable(cond03)())
    for n in range(ntasks):
        loop.create_task(cond02(n, barrier))
    await barrier  # All instances of cond02 have completed
    # Test wait_for
    barrier = asyn.Barrier(2)
    loop.create_task(cond04(99, barrier))
    await barrier
    # cancel continuously running coros.
    if new:
        t1.cancel()
        t3.cancel()
        await asyncio.sleep_ms(0)
    else:
        await asyn.Cancellable.cancel_all()
    print('Done.')

def condition_test(new=False):
    printexp('''cond02 0 Awaiting notification.
cond02 1 Awaiting notification.
cond02 2 Awaiting notification.
cond02 3 Awaiting notification.
cond02 4 Awaiting notification.
cond02 5 Awaiting notification.
cond02 6 Awaiting notification.
cond02 5 triggered. tim = 1
cond02 6 triggered. tim = 1
cond02 3 triggered. tim = 3
cond02 4 triggered. tim = 3
cond02 1 triggered. tim = 5
cond02 2 triggered. tim = 5
cond02 0 triggered. tim = 7
cond04 99 Awaiting notification and predicate.
cond04 99 triggered. tim = 9
Done.
''', 13)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(cond_go(loop, new))

# ************ Gather test ************

# Task with one positional arg. Demonstrate that result order depends on
# original list order not termination order.
async def gath01(n):
    print('gath01', n, 'started')
    await asyncio.sleep(3 - n/10)
    print('gath01', n, 'done')
    return n

# Takes kwarg. This is last to terminate.
async def gath02(x, y, rats):
    print('gath02 started')
    await asyncio.sleep(7)
    print('gath02 done')
    return x * y, rats

# Only quits on timeout
async def gath03(n):
    print('gath03 started')
    try:
        while True:
            await asyncio.sleep(1)
            n += 1
    except asyncio.TimeoutError:
        print('gath03 timeout')
        return n

async def gath_go():
    gatherables = [asyn.Gatherable(gath01, n) for n in range(4)]
    gatherables.append(asyn.Gatherable(gath02, 7, 8, rats=77))
    gatherables.append(asyn.Gatherable(gath03, 0, timeout=5))
    res = await asyn.Gather(gatherables)
    print(res)

def gather_test():
    printexp('''gath01 0 started
gath01 1 started
gath01 2 started
gath01 3 started
gath02 started
gath03 started
gath01 3 done
gath01 2 done
gath01 1 done
gath01 0 done
gath03 timeout
gath02 done
[0, 1, 2, 3, (56, 77), 4]
''', 7)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(gath_go())
