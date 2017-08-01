# aswitch.py Switch and pushbutton classes for asyncio
# Delay_ms A retriggerable delay class. Can schedule a coro on timeout.
# Switch Simple debounced switch class for normally open grounded switch.
# Pushbutton extend the above to support logical state, long press and
# double-click events
# Tested on Pyboard but should run on other microcontroller platforms
# running MicroPython and uasyncio.
# Author: Peter Hinch.
# Copyright Peter Hinch 2017 Released under the MIT license.

try:
    import asyncio_priority as asyncio
except ImportError:
    import uasyncio as asyncio
import utime as time
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
        self.tstop = time.ticks_add(loop.time(), duration)
        if not self._running:
            # Start a task which stops the delay after its period has elapsed
            loop.create_task(self.killer())
            self._running = True

    def running(self):
        return self._running

    async def killer(self):
        loop = asyncio.get_event_loop()
        twait = time.ticks_diff(self.tstop, loop.time())
        while twait > 0 and self._running:  # Return if stop() called during wait
            # Must loop here: might be retriggered
            await asyncio.sleep_ms(twait)
            twait = time.ticks_diff(self.tstop, loop.time())
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
        self.pin = pin  # Initialise for input
        self._true_func = False
        self._false_func = False
        self._double_func = False
        self._long_func = False
        self._single_func = False
        self.sense = pin.value()  # Convert from electrical to logical value
        self.btnstate = self.rawstate()  # Initial state
        self.state = 0
        loop = asyncio.get_event_loop()
        loop.create_task(self.buttoncheck())  # Thread runs forever

    def press_func(self, func, args=()):
        self._true_func = func
        self._true_args = args

    def release_func(self, func, args=()):
        self._false_func = func
        self._false_args = args

    def single_func(self, func, args=()):
        self._single_func = func
        self._single_args = args

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
        return self.btnstate

    async def buttoncheck(self):
        doubledelay = Delay_ms()
        longdelay = Delay_ms()
        while True:
            currentstate = self.rawstate()
            if self.state == 0 and currentstate is True:
                # Button is pressed first time
                self.state = 1
                longdelay.trigger(Pushbutton.long_press_ms)
            elif self.state == 1 and currentstate is False and longdelay.running():
                # Button was released before long press
                longdelay.stop()
                self.state = 2
                doubledelay.trigger(Pushbutton.double_click_ms)
            elif self.state == 2 and not doubledelay.running():
                # Double timer run out -> single click
                self.state = 0
                launch(self._single_func, self._single_args)
            elif self.state == 2 and currentstate is True and doubledelay.running():
                # Second click for double click was detected
                self.state = 3
            elif self.state == 3 and currentstate is False:
                # Wait for second click to be released
                self.state = 0
                launch(self._double_func, self._double_args)
            elif self.state == 1 and not longdelay.running():
                # Button was pressed and long delay timed out
                self.state = 4
            elif self.state == 4 and currentstate is False:
                # Wait for key release on long press
                self.state = 0
                launch(self._long_func, self._long_args)
            await asyncio.sleep_ms(Pushbutton.debounce_ms)
