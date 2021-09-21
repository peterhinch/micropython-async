# monitor_test.py

import uasyncio as asyncio
from monitor import monitor, mon_func, mon_call, set_uart

set_uart(2)  # Define interface to use

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
