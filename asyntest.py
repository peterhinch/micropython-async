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

from asyn import Event, Semaphore, BoundedSemaphore, Barrier

def print_tests():
    st = '''Available functions:
print_tests()  Print this list
ack_test()  Test event acknowledge
event_test(lp=True)  Test Event and Lock objects. If lp use low priority mechanism
barrier_test()  Test the Barrier class
semaphore_test(bounded=False) Test Semaphore or BoundedSemaphore

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
