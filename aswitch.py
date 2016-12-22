# aswitch.py Switch and pushbutton classes for asyncio
# Delay_ms A retriggerable delay class. Can schedule a coro on timeout.
# Switch Simple debounced switch class for normally open grounded switch.
# Pushbutton extend the above to support logical state, long press and
# double-click events
# Tested on Pyboard but should run on other microcontroller platforms
# running MicroPython and uasyncio.
# Author: Peter Hinch.
# Copyright Peter Hinch 2016 Released under the MIT license.

import uasyncio as asyncio
from asyn import launch
# launch: run a callback or initiate a coroutine depending on which is passed.


class Delay_ms(object):
    def __init__(self, func=None, args=()):
        self.func = func
        self.args = args
        self._running = False

    def stop(self):
        self._running = False

    def trigger(self, duration):  # Update end time
        loop = asyncio.get_event_loop()
        self.tstop = loop.time() + duration
        if not self._running:
            # Start a thread which stops the delay after its period has elapsed
            loop.create_task(self.killer())
            self._running = True

    def running(self):
        return self._running

    async def killer(self):
        loop = asyncio.get_event_loop()
        while self.tstop > loop.time():
            # Must loop here: might be retriggered
            await asyncio.sleep_ms(self.tstop - loop.time())
        if self._running and self.func is not None:
            launch(self.func, self.args)  # Execute callback
        self._running = False


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
                if state == 0 and self.close_func:
                    launch(self._close_func, self._close_args)
                elif state == 1 and self._open_func:
                    launch(self._open_func, self._open_args)
            # Ignore further state changes until switch has settled
            await asyncio.sleep_ms(Switch.debounce_ms)

class Pushbutton(object):
    debounce_ms = 50
    long_press_ms = 1000
    double_click_ms = 400
    def __init__(self, pin):
        self.pin = pin # Initialise for input
        self._true_func = False
        self._false_func = False
        self._double_func = False
        self._long_func = False
        self.sense = pin.value()  # Convert from electrical to logical value
        self.buttonstate = self.rawstate()  # Initial state
        loop = asyncio.get_event_loop()
        loop.create_task(self.buttoncheck())  # Thread runs forever

    def press_func(self, func, args=()):
        self._true_func = func
        self._true_args = args

    def release_func(self, func, args=()):
        self._false_func = func
        self._false_args = args

    def double_func(self, func, args=()):
        self._double_func = func
        self._double_args = args

    def long_func(self, func, args=()):
        self._long_func = func
        self._long_args = args

    # Current non-debounced logical button state: True == pressed
    def rawstate(self):
        return bool(self.pin.value() ^ self.sense)

    # Current debounced state of button (True == pressed)
    def __call__(self):
        return self.buttonstate

    async def buttoncheck(self):
        loop = asyncio.get_event_loop()
        if self._long_func:
            longdelay = Delay_ms(self._long_func, self._long_args)
        if self._double_func:
            doubledelay = Delay_ms()
        while True:
            state = self.rawstate()
            # State has changed: act on it now.
            if state != self.buttonstate:
                self.buttonstate = state
                if state:
                    # Button is pressed
                    if self._long_func and not longdelay.running():
                        # Start long press delay
                        longdelay.trigger(Pushbutton.long_press_ms)
                    if self._double_func:
                        if doubledelay.running():
                            launch(self._double_func, self._double_args)
                        else:
                            # First click: start doubleclick timer
                            doubledelay.trigger(Pushbutton.double_click_ms)
                    if self._true_func:
                        launch(self._true_func, self._true_args)
                else:
                    # Button release
                    if self._long_func and longdelay.running():
                        # Avoid interpreting a second click as a long push
                        longdelay.stop()
                    if self._false_func:
                        launch(self._false_func, self._false_args)
            # Ignore state changes until switch has settled
            await asyncio.sleep_ms(Pushbutton.debounce_ms)
