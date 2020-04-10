import uasyncio as asyncio
import utime as time
from . import launch
# Usage:
# from primitives.delay_ms import Delay_ms

class Delay_ms:
    verbose = False
    def __init__(self, func=None, args=(), can_alloc=True, duration=1000):
        self.func = func
        self.args = args
        self.can_alloc = can_alloc
        self.duration = duration  # Default duration
        self._tstop = None  # Killer not running
        self._running = False  # Timer not running
        if not can_alloc:
            asyncio.create_task(self._run())

    async def _run(self):
        while True:
            if not self._running:  # timer not running
                await asyncio.sleep_ms(0)
            else:
                await self._killer()

    def stop(self):
        self._running = False
        # If uasyncio is ever fixed we should cancel .killer

    def trigger(self, duration=0):  # Update end time
        self._running = True
        if duration <= 0:
            duration = self.duration
        tn = time.ticks_add(time.ticks_ms(), duration)  # new end time
        self.verbose and self._tstop is not None and self._tstop > tn \
            and print("Warning: can't reduce Delay_ms time.")
        # Start killer if can allocate and killer is not running
        sk = self.can_alloc and self._tstop is None
        # The following indicates ._killer is running: it will be
        # started either here or in ._run
        self._tstop = tn
        if sk:  # ._killer stops the delay when its period has elapsed
            asyncio.create_task(self._killer())

    def running(self):
        return self._running

    __call__ = running

    async def _killer(self):
        twait = time.ticks_diff(self._tstop, time.ticks_ms())
        while twait > 0:  # Must loop here: might be retriggered
            await asyncio.sleep_ms(twait)
            if self._tstop is None:
                break  # Return if stop() called during wait
            twait = time.ticks_diff(self._tstop, time.ticks_ms())
        if self._running and self.func is not None:
            launch(self.func, self.args)  # Timed out: execute callback
        self._tstop = None  # killer not running
        self._running = False  # timer is stopped
