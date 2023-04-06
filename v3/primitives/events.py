# events.py Event based primitives

# Copyright (c) 2022 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
from . import Delay_ms

# An Event-like class that can wait on an iterable of Event-like instances.
# .wait pauses until any passed event is set.
class WaitAny:
    def __init__(self, events):
        self.events = events
        self.trig_event = None
        self.evt = asyncio.Event()

    async def wait(self):
        tasks = [asyncio.create_task(self.wt(event)) for event in self.events]
        try:
            await self.evt.wait()
        finally:
            self.evt.clear()
            for task in tasks:
                task.cancel()
        return self.trig_event

    async def wt(self, event):
        await event.wait()
        self.evt.set()
        self.trig_event = event
 
    def event(self):
        return self.trig_event

    def clear(self):
        for evt in (x for x in self.events if hasattr(x, 'clear')):
            evt.clear()

# An Event-like class that can wait on an iterable of Event-like instances,
# .wait pauses until all passed events have been set.
class WaitAll:
    def __init__(self, events):
        self.events = events

    async def wait(self):
        async def wt(event):
            await event.wait()
        tasks = (asyncio.create_task(wt(event)) for event in self.events)
        try:
            await asyncio.gather(*tasks)
        finally:  # May be subject to timeout or cancellation
            for task in tasks:
                task.cancel()

    def clear(self):
        for evt in (x for x in self.events if hasattr(x, 'clear')):
            evt.clear()

# Minimal switch class having an Event based interface
class ESwitch:
    debounce_ms = 50

    def __init__(self, pin, lopen=1):  # Default is n/o switch returned to gnd
        self._pin = pin # Should be initialised for input with pullup
        self._lopen = lopen  # Logic level in "open" state
        self.open = asyncio.Event()
        self.close = asyncio.Event()
        self._state = self._pin() ^ self._lopen  # Get initial state
        asyncio.create_task(self._poll(ESwitch.debounce_ms))

    async def _poll(self, dt):  # Poll the button
        while True:
            if (s := self._pin() ^ self._lopen) != self._state:  # 15μs
                self._state = s
                self._cf() if s else self._of()
            await asyncio.sleep_ms(dt)  # Wait out bounce

    def _of(self):
        self.open.set()

    def _cf(self):
        self.close.set()

    # ***** API *****
    # Return current state of switch (0 = pressed)
    def __call__(self):
        return self._state

    def deinit(self):
        self._poll.cancel()
        self.open.clear()
        self.close.clear()

# Minimal pushbutton class having an Event based interface
class EButton:
    debounce_ms = 50  # Attributes can be varied by user
    long_press_ms = 1000
    double_click_ms = 400

    def __init__(self, pin, suppress=False, sense=None):
        self._pin = pin  # Initialise for input
        self._supp = suppress
        self._sense = pin() if sense is None else sense
        self._state = self.rawstate()  # Initial logical state
        self._ltim = Delay_ms(duration = EButton.long_press_ms)
        self._dtim = Delay_ms(duration = EButton.double_click_ms)
        self.press = asyncio.Event()  # *** API ***
        self.double = asyncio.Event()
        self.long = asyncio.Event()
        self.release = asyncio.Event()  # *** END API ***
        self._tasks = [asyncio.create_task(self._poll(EButton.debounce_ms))]  # Tasks run forever. Poll contacts
        self._tasks.append(asyncio.create_task(self._ltf()))  # Handle long press
        if suppress:
            self._tasks.append(asyncio.create_task(self._dtf()))  # Double timer

    async def _poll(self, dt):  # Poll the button
        while True:
            if (s := self.rawstate()) != self._state:
                self._state = s
                self._pf() if s else self._rf()
            await asyncio.sleep_ms(dt)  # Wait out bounce

    def _pf(self):  # Button press
        if not self._supp:
            self.press.set()  # User event
        if self._dtim():  # Press occurred while _dtim is running
            self.double.set()  # User event
            self._dtim.stop()  # _dtim's Event is only used if suppress
        else:  # Single press or 1st of a double pair.
            self._dtim.trigger()
            self._ltim.trigger()  # Trigger long timer on 1st press of a double pair

    def _rf(self):  # Button release
        self._ltim.stop()
        if not self._supp or not self._dtim():  # If dtim running postpone release otherwise it
            self.release.set()  # is set before press

    async def _ltf(self):  # Long timeout
        while True:
            await self._ltim.wait()
            self._ltim.clear()  # Clear the event
            self.long.set()  # User event
            
    # Runs if suppress set. Delay response to single press until sure it is a single short pulse.
    async def _dtf(self):
        while True:
            await self._dtim.wait()  # Double click has timed out
            self._dtim.clear()  # Clear the event
            if not self._ltim():  # Button was released: not a long press.
                self.press.set()  # User events
                self.release.set()

    # ****** API ******
    # Current non-debounced logical button state: True == pressed
    def rawstate(self):
        return bool(self._pin() ^ self._sense)

    # Current debounced state of button (True == pressed)
    def __call__(self):
        return self._state

    def deinit(self):
        for task in self._tasks:
            task.cancel()
        for evt in (self.press, self.double, self.long, self.release):
            evt.clear()
