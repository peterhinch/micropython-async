# barrier.py
# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Now uses Event rather than polling.

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from . import launch

# A Barrier synchronises N coros. Each issues await barrier.
# Execution pauses until all other participant coros are waiting on it.
# At that point the callback is executed. Then the barrier is 'opened' and
# execution of all participants resumes.

class Barrier():
    def __init__(self, participants, func=None, args=()):
        self._participants = participants
        self._func = func
        self._args = args
        self._reset(True)
        self._res = None
        self._evt = asyncio.Event()

    def __await__(self):
        if self.trigger():
            return

        direction = self._down
        while True:  # Wait until last waiting task changes the direction
            if direction != self._down:
                return
            await self._evt.wait()
            self._evt.clear()

    __iter__ = __await__

    def result(self):
        return self._res

    def trigger(self):
        self._count += -1 if self._down else 1
        if self._count < 0 or self._count > self._participants:
            raise ValueError('Too many tasks accessing Barrier')
        self._evt.set()
        if self._at_limit():  # All other tasks are also at limit
            if self._func is not None:
                self._res = launch(self._func, self._args)
            self._reset(not self._down)  # Toggle direction to release others
            return True
        return False

    def _reset(self, down):
        self._down = down
        self._count = self._participants if down else 0

    def busy(self):
        if self._down:
            done = self._count == self._participants
        else:
            done = self._count == 0
        return not done

    def _at_limit(self):  # Has count reached up or down limit?
        limit = 0 if self._down else self._participants
        return self._count == limit
