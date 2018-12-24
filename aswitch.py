# aswitch.py Switch and pushbutton classes for asyncio
# Delay_ms A retriggerable delay class. Can schedule a coro on timeout.
# Switch Simple debounced switch class for normally open grounded switch.
# Pushbutton extend the above to support logical state, long press and
# double-click events
# Tested on Pyboard but should run on other microcontroller platforms
# running MicroPython and uasyncio.

# The MIT License (MIT)
#
# Copyright (c) 2017 Peter Hinch
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import uasyncio as asyncio
import utime as time
# Remove dependency on asyn to save RAM:
# launch: run a callback or initiate a coroutine depending on which is passed.
async def _g():
    pass
type_coro = type(_g())

# If a callback is passed, run it and return.
# If a coro is passed initiate it and return.
# coros are passed by name i.e. not using function call syntax.
def launch(func, tup_args):
    res = func(*tup_args)
    if isinstance(res, type_coro):
        loop = asyncio.get_event_loop()
        loop.create_task(res)


class Delay_ms(object):
    def __init__(self, func=None, args=(), can_alloc=True, duration=1000):
        self.func = func
        self.args = args
        self.can_alloc = can_alloc
        self.duration = duration  # Default duration
        self.tstop = None  # Not running
        self.loop = asyncio.get_event_loop()
        if not can_alloc:
            self.loop.create_task(self._run())

    async def _run(self):
        while True:
            if self.tstop is None:  # Not running
                await asyncio.sleep_ms(0)
            else:
                await self.killer()

    def stop(self):
        self.tstop = None

    def trigger(self, duration=0):  # Update end time
        if duration <= 0:
            duration = self.duration
        if self.can_alloc and self.tstop is None:  # No killer task is running
            self.tstop = time.ticks_add(time.ticks_ms(), duration)
            # Start a task which stops the delay after its period has elapsed
            self.loop.create_task(self.killer())
        self.tstop = time.ticks_add(time.ticks_ms(), duration)

    def running(self):
        return self.tstop is not None

    __call__ = running

    async def killer(self):
        twait = time.ticks_diff(self.tstop, time.ticks_ms())
        while twait > 0:  # Must loop here: might be retriggered
            await asyncio.sleep_ms(twait)
            if self.tstop is None:
                break  # Return if stop() called during wait
            twait = time.ticks_diff(self.tstop, time.ticks_ms())
        if self.tstop is not None and self.func is not None:
            launch(self.func, self.args)  # Timed out: execute callback
        self.tstop = None  # Not running

class Switch(object):
    debounce_ms = 50
    def __init__(self, pin):
        self.pin = pin # Should be initialised for input with pullup
        self._open_func = False
        self._close_func = False
        self.switchstate = self.pin.value()  # Get initial state
        loop = asyncio.get_event_loop()
        loop.create_task(self.switchcheck())  # Thread runs forever

    def open_func(self, func, args=()):
        self._open_func = func
        self._open_args = args

    def close_func(self, func, args=()):
        self._close_func = func
        self._close_args = args

    # Return current state of switch (0 = pressed)
    def __call__(self):
        return self.switchstate

    async def switchcheck(self):
        loop = asyncio.get_event_loop()
        while True:
            state = self.pin.value()
            if state != self.switchstate:
                # State has changed: act on it now.
                self.switchstate = state
                if state == 0 and self._close_func:
                    launch(self._close_func, self._close_args)
                elif state == 1 and self._open_func:
                    launch(self._open_func, self._open_args)
            # Ignore further state changes until switch has settled
            await asyncio.sleep_ms(Switch.debounce_ms)

class Pushbutton(object):
    debounce_ms = 50
    long_press_ms = 1000
    double_click_ms = 400
    def __init__(self, pin, suppress=False):
        self.pin = pin # Initialise for input
        self._supp = suppress
        self._dblpend = False  # Doubleclick waiting for 2nd click
        self._dblran = False  # Doubleclick executed user function
        self._tf = False
        self._ff = False
        self._df = False
        self._lf = False
        self._ld = False  # Delay_ms instance for long press
        self._dd = False  # Ditto for doubleclick
        self.sense = pin.value()  # Convert from electrical to logical value
        self.state = self.rawstate()  # Initial state
        loop = asyncio.get_event_loop()
        loop.create_task(self.buttoncheck())  # Thread runs forever

    def press_func(self, func, args=()):
        self._tf = func
        self._ta = args

    def release_func(self, func, args=()):
        self._ff = func
        self._fa = args

    def double_func(self, func, args=()):
        self._df = func
        self._da = args

    def long_func(self, func, args=()):
        self._lf = func
        self._la = args

    # Current non-debounced logical button state: True == pressed
    def rawstate(self):
        return bool(self.pin.value() ^ self.sense)

    # Current debounced state of button (True == pressed)
    def __call__(self):
        return self.state

    def _ddto(self):  # Doubleclick timeout: no doubleclick occurred
        self._dblpend = False
        if self._supp and not self.state:
            if not self._ld or (self._ld and not self._ld()):
                launch(self._ff, self._fa)

    async def buttoncheck(self):
        if self._lf:  # Instantiate timers if funcs exist
            self._ld = Delay_ms(self._lf, self._la)
        if self._df:
            self._dd = Delay_ms(self._ddto)
        while True:
            state = self.rawstate()
            # State has changed: act on it now.
            if state != self.state:
                self.state = state
                if state:  # Button pressed: launch pressed func
                    if self._tf:
                        launch(self._tf, self._ta)
                    if self._lf:  # There's a long func: start long press delay
                        self._ld.trigger(Pushbutton.long_press_ms)
                    if self._df:
                        if self._dd():  # Second click: timer running
                            self._dd.stop()
                            self._dblpend = False
                            self._dblran = True  # Prevent suppressed launch on release
                            launch(self._df, self._da)
                        else:
                            # First click: start doubleclick timer
                            self._dd.trigger(Pushbutton.double_click_ms)
                            self._dblpend = True  # Prevent suppressed launch on release
                else:  # Button release. Is there a release func?
                    if self._ff:
                        if self._supp:
                            d = self._ld 
                            # If long delay exists, is running and doubleclick status is OK
                            if not self._dblpend and not self._dblran:
                                if (d and d()) or not d:
                                    launch(self._ff, self._fa)
                        else:
                            launch(self._ff, self._fa)
                    if self._ld:
                        self._ld.stop()  # Avoid interpreting a second click as a long push
                    self._dblran = False
            # Ignore state changes until switch has settled
            await asyncio.sleep_ms(Pushbutton.debounce_ms)
