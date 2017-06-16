# exit_gate_test.py Test/demo of the ExitGate class
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license
import uasyncio as asyncio
from utime import ticks_ms, ticks_diff
from asyn import ExitGate

async def bar(exit_gate, t):
    async with exit_gate:
        result = 'normal' if await exit_gate.sleep(t) else 'abort'
    tim = ticks_diff(ticks_ms(), tstart) / 1000
    print('{:5.2f} bar() with time value {} completed. Result {}.'.format(tim, t, result))

async def foo():
    exit_gate = ExitGate()
    loop = asyncio.get_event_loop()
    for t in range(1, 10):
        loop.create_task(bar(exit_gate, t))
    print('Task queue length = ', len(loop.q))
    await asyncio.sleep(3)
    print('Task queue length = ', len(loop.q))
    print('Now foo is causing tasks to terminate.')
    await exit_gate
    print('foo() complete.')
    print('Task queue length = ', len(loop.q))


tstart = ticks_ms()
loop = asyncio.get_event_loop()
loop.run_until_complete(foo())
