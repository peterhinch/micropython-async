# message.py

# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
# Usage:
# from primitives.message import Message

# A coro waiting on a message issues await message
# A coro rasing the message issues message.set(payload)
# When all waiting coros have run
# message.clear() should be issued

# This more efficient version is commented out because Event.set is not ISR
# friendly. TODO If it gets fixed, reinstate this (tested) version and update
# tutorial for 1:n operation.
#class Message(asyncio.Event):
    #def __init__(self, _=0):
        #self._data = None
        #super().__init__()

    #def clear(self):
        #self._data = None
        #super().clear()

    #def __await__(self):
        #await super().wait()

    #__iter__ = __await__

    #def set(self, data=None):
        #self._data = data
        #super().set()

    #def value(self):
        #return self._data

# Has an ISR-friendly .set()
class Message():
    def __init__(self, delay_ms=0):
        self.delay_ms = delay_ms
        self.clear()

    def clear(self):
        self._flag = False
        self._data = None

    async def wait(self):  # CPython comptaibility
        while not self._flag:
            await asyncio.sleep_ms(self.delay_ms)

    def __await__(self):
        while not self._flag:
            await asyncio.sleep_ms(self.delay_ms)

    __iter__ = __await__

    def is_set(self):
        return self._flag

    def set(self, data=None):
        self._flag = True
        self._data = data

    def value(self):
        return self._data
