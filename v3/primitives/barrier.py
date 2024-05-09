# barrier.py
# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Now uses Event rather than polling.

import asyncio

from . import launch

# A Barrier synchronises N coros. Each issues await barrier.
# Execution pauses until all other participant coros are waiting on it.
# At that point the callback is executed. Then the barrier is 'opened' and
# execution of all participants resumes.


class Barrier:
    def __init__(self, participants, func=None, args=()):
        self._participants = participants
        self._count = participants
        self._func = func
        self._args = args
        self._res = None
        self._evt = asyncio.Event()

    def __await__(self):
        if self.trigger():
            return  # Other tasks have already reached barrier
        await self._evt.wait()  # Wait until last task reaches it

    __iter__ = __await__

    def result(self):
        return self._res

    def trigger(self):
        self._count -= 1
        if self._count < 0:
            raise ValueError("Too many tasks accessing Barrier")
        if self._count > 0:
            return False  # At least 1 other task has not reached barrier
        # All other tasks are waiting
        if self._func is not None:
            self._res = launch(self._func, self._args)
        self._count = self._participants
        self._evt.set()  # Release others
        self._evt.clear()
        return True

    def busy(self):
        return self._count < self._participants
