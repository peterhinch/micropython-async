# message.py
# Now uses ThreadSafeFlag for efficiency

# Copyright (c) 2018-2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Usage:
# from primitives.message import Message

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

# A coro waiting on a message issues await message
# A coro or hard/soft ISR raising the message issues.set(payload)
# .clear() should be issued by at least one waiting task and before
# next event.

class Message(asyncio.ThreadSafeFlag):
    def __init__(self, _=0):  # Arg: poll interval. Compatibility with old code.
        self._evt = asyncio.Event()
        self._data = None  # Message
        self._state = False  # Ensure only one task waits on ThreadSafeFlag
        self._is_set = False  # For .is_set()
        super().__init__()

    def clear(self):  # At least one task must call clear when scheduled
        self._state = False
        self._is_set = False

    def __iter__(self):
        yield from self.wait()
        return self._data
    
    async def wait(self):
        if self._state:  # A task waits on ThreadSafeFlag
            await self._evt.wait()  # Wait on event
        else:  # First task to wait
            self._state = True
            # Ensure other tasks see updated ._state before they wait
            await asyncio.sleep_ms(0)
            await super().wait()  # Wait on ThreadSafeFlag
            self._evt.set()
            self._evt.clear()
        return self._data

    def set(self, data=None):  # Can be called from a hard ISR
        self._data = data
        self._is_set = True
        super().set()

    def is_set(self):
        return self._is_set

    def value(self):
        return self._data
