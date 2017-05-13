# awaitable.py Demo of an awaitable class
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license
# runs in CPython and MicroPython
# Trivial fix for MicroPython issue #2678

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

class Hardware(object):
    def __init__(self, count):
        self.count = count

    def __await__(self):  # Typical use, loop until an interface becomes ready.
        while self.count:
            print(self.count)
            yield
            self.count -= 1

    __iter__ = __await__  # issue #2678

loop = asyncio.get_event_loop()

hardware = Hardware(10)

async def run():
    await hardware
    print('Done')

loop.run_until_complete(run())
