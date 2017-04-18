# asyntest.py Test/demo of the 'micro' Lock, Event, Barrier and Semaphore classes
# Author: Peter Hinch
# Copyright Peter Hinch 2016 Released under the MIT license

# Tests:
# ack_test()
# event_test()
# barrier_test()
# semaphore_test()  Pass True to test BoundedSemaphore class
# Issue ctrl-D after running each test

# CPython 3.5 compatibility
# (ignore RuntimeWarning: coroutine '_g' was never awaited)
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from asyn import Lock, Event, Semaphore, BoundedSemaphore, Barrier

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
    print("I've seen starships burn off the shoulder of Orion...")
    print("Time to die...")

def ack_test():
    loop = asyncio.get_event_loop()
    loop.create_task(run_ack())
    loop.run_until_complete(ack_coro(10))

# ************ Test Lock and Event classes ************

async def run_lock(n, lock):
    print('run_lock {} waiting for lock'.format(n))
    async with lock:
        print('run_lock {} acquired lock'.format(n))
        await asyncio.sleep(1)  # Delay to demo other coros waiting for lock
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
    lock = Lock()
    loop.create_task(run_lock(1, lock))
    loop.create_task(run_lock(2, lock))
    loop.create_task(run_lock(3, lock))
    print('Test Event class')
    event = Event(True)  # Use low priority scheduling if available
    print('got here')
    loop.create_task(eventset(event))
    print('gh1')
    await eventwait(event)  # run_event_test runs fast until this point
    print('Event status {}'.format('Incorrect' if event.is_set() else 'OK'))
    print('Tasks complete')

def event_test():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_event_test())

# ************ Barrier test ************

async def killer(duration):
    await asyncio.sleep(duration)

def callback(text):
    print(text)

barrier = Barrier(3, callback, ('Synch',))

async def report():
    for i in range(5):
        print('{} '.format(i), end='')
        await barrier

def barrier_test():
    loop = asyncio.get_event_loop()
    for _ in range(3):
        loop.create_task(report())
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
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_sema_test(bounded))
