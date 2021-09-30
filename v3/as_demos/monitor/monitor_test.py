# monitor_test.py

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
from monitor import monitor, monitor_init, mon_func, mon_call, set_device

set_device(UART(2, 1_000_000))  # UART must be 1MHz

@monitor(1, 2)
async def foo(t):
    await asyncio.sleep_ms(t)
    return t * 2

@monitor(3)
async def bar(t):
    await asyncio.sleep_ms(t)
    return t * 2

@monitor(4)
async def forever():
    while True:
        await asyncio.sleep(1)

class Foo:
    def __init__(self):
        pass
    @monitor(5, 1)
    async def rats(self):
        await asyncio.sleep(1)
        print('rats ran')

@mon_func(20)
def sync_func():
    pass

def another_sync_func():
    pass

async def main():
    monitor_init()
    sync_func()
    with mon_call(22):
        another_sync_func()
    while True:
        myfoo = Foo()
        asyncio.create_task(myfoo.rats())
        ft = asyncio.create_task(foo(1000))
        bt = asyncio.create_task(bar(200))
        print('bar', await bt)
        ft.cancel()
        print('got', await foo(2000))
        try:
            await asyncio.wait_for(forever(), 3)
        except asyncio.TimeoutError:  # Mandatory error trapping
            print('got timeout')  # Caller sees TimeoutError

asyncio.run(main())
