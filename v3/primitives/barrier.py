try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from . import launch

# A Barrier synchronises N coros. Each issues await barrier.
# Execution pauses until all other participant coros are waiting on it.
# At that point the callback is executed. Then the barrier is 'opened' and
# execution of all participants resumes.

# The nowait arg is to support task cancellation. It enables usage where one or
# more coros can register that they have reached the barrier without waiting
# for it. Any coros waiting normally on the barrier will pause until all
# non-waiting coros have passed the barrier and all waiting ones have reached
# it. The use of nowait promotes efficiency by enabling tasks which have been
# cancelled to leave the task queue as soon as possible.

class Barrier():
    def __init__(self, participants, func=None, args=()):
        self._participants = participants
        self._func = func
        self._args = args
        self._reset(True)

    def __await__(self):
        self._update()
        if self._at_limit():  # All other threads are also at limit
            if self._func is not None:
                launch(self._func, self._args)
            self._reset(not self._down)  # Toggle direction to release others
            return

        direction = self._down
        while True:  # Wait until last waiting thread changes the direction
            if direction != self._down:
                return
            await asyncio.sleep_ms(0)

    __iter__ = __await__

    def trigger(self):
        self._update()
        if self._at_limit():  # All other threads are also at limit
            if self._func is not None:
                launch(self._func, self._args)
            self._reset(not self._down)  # Toggle direction to release others

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

    def _update(self):
        self._count += -1 if self._down else 1
        if self._count < 0 or self._count > self._participants:
            raise ValueError('Too many tasks accessing Barrier')
