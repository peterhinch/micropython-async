# runs in CPython
# In Unix MicroPython fails with
# TypeError: 'Hardware' object is not iterable
# Fixed by supplying __iter__()

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

class Hardware(object):
    def __init__(self, count):
        self.count = count

    def __iter__(self):  # issue #2678
        yield from self.__await__()

    def __await__(self):  # Typical use, loop until an interface becomes ready.
        while self.count:
            print(self.count)
            yield
            self.count -= 1

loop = asyncio.get_event_loop()

hardware = Hardware(10)

async def run():
    await hardware
    print('Done')

loop.run_until_complete(run())
