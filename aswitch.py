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

class Pushbutton:
    debounce_ms = 50
    long_press_ms = 1000
    double_click_ms = 400

    def __init__(self, pin, suppress=False):
        self.pin = pin
        self._supp = suppress  # don't call release func after long press
        self._tf = None  # pressed function
        self._ff = None  # released function
        self._df = None  # double pressed function
        self._lf = None  # long pressed function
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

    async def buttoncheck(self):
        t_change = None
        supp = False
        clicks = 0
        lpr = False  # long press ran
        ####
        # local functions for performance improvements
        deb = self.debounce_ms
        dcms = self.double_click_ms
        lpms = self.long_press_ms
        raw = self.rawstate
        ticks_diff = time.ticks_diff
        ticks_ms = time.ticks_ms
        ###
        while True:
            state = raw()
            if state is False and self.state is False and self._supp and \
                    ticks_diff(ticks_ms(), t_change) > dcms and clicks > 0 and self._ff:
                clicks = 0
                launch(self._ff, self._fa)
            elif state is True and self.state is True:
                if clicks > 0 and ticks_diff(ticks_ms(), t_change) > dcms:
                    # double click timeout
                    clicks = 0
                if self._lf and lpr is False:  # check long press
                    if ticks_diff(ticks_ms(), t_change) >= lpms:
                        lpr = True
                        clicks = 0
                        if self._supp is True:
                            supp = True
                        launch(self._lf, self._la)
            elif state != self.state:  # state changed
                lpr = False
                self.state = state
                if state is True:  # Button pressed: launch pressed func
                    if ticks_diff(ticks_ms(), t_change) > dcms:
                        clicks = 0
                    if self._df:
                        clicks += 1
                    if clicks == 2:  # double click
                        clicks = 0
                        if self._supp is True:
                            supp = True
                        launch(self._df, self._da)
                    elif self._tf:
                        launch(self._tf, self._ta)
                else:  # Button released. launch release func
                    if supp is True:
                        supp = False
                    elif clicks and self._supp > 0:
                        pass
                    elif self._ff:  # not after a long press with suppress
                        launch(self._ff, self._fa)
                t_change = ticks_ms()
            # Ignore state changes until switch has settled
            await asyncio.sleep_ms(deb)
