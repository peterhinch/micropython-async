# delay_test.py Tests for Delay_ms class

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import micropython
from primitives.delay_ms import Delay_ms

micropython.alloc_emergency_exception_buf(100)

def printexp(exp, runtime=0):
    print('Expected output:')
    print('\x1b[32m')
    print(exp)
    print('\x1b[39m')
    if runtime:
        print('Running (runtime = {}s):'.format(runtime))
    else:
        print('Running (runtime < 1s):')

async def ctor_test():  # Constructor arg
    s = '''
Trigger 5 sec delay
Retrigger 5 sec delay
Callback should run
cb callback
Done
'''
    printexp(s, 12)
    def cb(v):
        print('cb', v)

    d = Delay_ms(cb, ('callback',), duration=5000)

    print('Trigger 5 sec delay')
    d.trigger()
    await asyncio.sleep(4)
    print('Retrigger 5 sec delay')
    d.trigger()
    await asyncio.sleep(4)
    print('Callback should run')
    await asyncio.sleep(2)
    print('Done')

async def launch_test():
    s = '''
Trigger 5 sec delay
Coroutine should run: run to completion.
Coroutine starts
Coroutine ends
Coroutine should run: test cancellation.
Coroutine starts
Coroutine should run: test awaiting.
Coroutine starts
Coroutine ends
Done
'''
    printexp(s, 20)
    async def cb(v, ms):
        print(v, 'starts')
        await asyncio.sleep_ms(ms)
        print(v, 'ends')

    d = Delay_ms(cb, ('coroutine', 1000))

    print('Trigger 5 sec delay')
    d.trigger(5000)  # Test extending time
    await asyncio.sleep(4)
    print('Coroutine should run: run to completion.')
    await asyncio.sleep(3)
    d = Delay_ms(cb, ('coroutine', 3000))
    d.trigger(5000)
    await asyncio.sleep(4)
    print('Coroutine should run: test cancellation.')
    await asyncio.sleep(2)
    coro = d.rvalue()
    coro.cancel()
    d.trigger(5000)
    await asyncio.sleep(4)
    print('Coroutine should run: test awaiting.')
    await asyncio.sleep(2)
    coro = d.rvalue()
    await coro
    print('Done')


async def reduce_test():  # Test reducing a running delay
    s = '''
Trigger 5 sec delay
Callback should run
cb callback
Callback should run
cb callback
Done
'''
    printexp(s, 11)
    def cb(v):
        print('cb', v)

    d = Delay_ms(cb, ('callback',))

    print('Trigger 5 sec delay')
    d.trigger(5000)  # Test extending time
    await asyncio.sleep(4)
    print('Callback should run')
    await asyncio.sleep(2)
    d.trigger(10000)
    await asyncio.sleep(1)
    d.trigger(3000)
    await asyncio.sleep(2)
    print('Callback should run')
    await asyncio.sleep(2)
    print('Done')


async def stop_test():  # Test the .stop and .running methods
    s = '''
Trigger 5 sec delay
Running
Callback should run
cb callback
Callback returned 42
Callback should not run
Done
    '''
    printexp(s, 12)
    def cb(v):
        print('cb', v)
        return 42

    d = Delay_ms(cb, ('callback',))

    print('Trigger 5 sec delay')
    d.trigger(5000)  # Test extending time
    await asyncio.sleep(4)
    if d():
        print('Running')
    print('Callback should run')
    await asyncio.sleep(2)
    print('Callback returned', d.rvalue())
    d.trigger(3000)
    await asyncio.sleep(1)
    d.stop()
    await asyncio.sleep(1)
    if d():
        print('Running')
    print('Callback should not run')
    await asyncio.sleep(4)
    print('Done')


async def isr_test():  # Test trigger from hard ISR
    from pyb import Timer
    s = '''
Timer holds off cb for 5 secs
cb should now run
cb callback
Done
'''
    printexp(s, 6)
    def cb(v):
        print('cb', v)

    d = Delay_ms(cb, ('callback',))

    def timer_cb(_):
        d.trigger(200)
    tim = Timer(1, freq=10, callback=timer_cb)

    print('Timer holds off cb for 5 secs')
    await asyncio.sleep(5)
    tim.deinit()
    print('cb should now run')
    await asyncio.sleep(1)
    print('Done')

async def err_test():  # Test triggering de-initialised timer
    s = '''
Running (runtime = 3s):
Trigger 1 sec delay
cb callback
Success: error was raised.
Done
    '''
    printexp(s, 3)
    def cb(v):
        print('cb', v)
        return 42

    d = Delay_ms(cb, ('callback',))

    print('Trigger 1 sec delay')
    d.trigger(1000)
    await asyncio.sleep(2)
    d.deinit()
    try:
        d.trigger(1000)
    except RuntimeError:
        print("Success: error was raised.")
    print('Done')

av = '''
Run a test by issuing
delay_test.test(n)
where n is a test number. Avaliable tests:
\x1b[32m
0 Test triggering from a hard ISR (Pyboard only)
1 Test the .stop method and callback return value.
2 Test reducing the duration of a running timer
3 Test delay defined by constructor arg
4 Test triggering a Task
5 Attempt to trigger de-initialised instance
\x1b[39m
'''
print(av)

tests = (isr_test, stop_test, reduce_test, ctor_test, launch_test, err_test)
def test(n=0):
    try:
        asyncio.run(tests[n]())
    finally:
        asyncio.new_event_loop()
