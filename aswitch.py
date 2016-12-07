# aswitch.py Switch and pushbutton classes for asyncio
# Delay_ms A retriggerable delay class. Can schedule a coro on timeout.
# Switch Simple debounced switch class for normally open grounded switch.

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

class Delay_ms(object):
    def __init__(self, coro=None, coro_args=()):
        self.loop = asyncio.get_event_loop()
        self.coro = coro
        self.coro_args = coro_args
        self._running = False

    def stop(self):
        self._running = False

    def trigger(self, duration):  # Update end time
        self.tstop = self.loop.time() + duration
        if not self._running:
            # Start a thread which stops the delay after its period has elapsed
            self.loop.call_soon(self.killer())
            self._running = True

    def running(self):
        return self._running

    async def killer(self):
        loop = self.loop
        while self.tstop > self.loop.time():
            # Must loop here: might be retriggered
            await asyncio.sleep_ms(self.tstop - self.loop.time())
        if self._running and self.coro is not None:
            loop.call_soon(self.coro(*self.coro_args))
        self._running = False


class Switch(object):
    debounce_ms = 50
    def __init__(self, pin):
        self.loop = asyncio.get_event_loop()
        self.pin = pin # Should be initialised for input with pullup
        self._open_coro = False
        self._close_coro = False
        self.switchstate = self.pin.value()  # Get initial state
        self.loop.call_soon(self.switchcheck())  # Thread runs forever

    def open_coro(self, coro, args=()):
        self._open_coro = coro
        self._open_coro_args = args

    def close_coro(self, coro, args=()):
        self._close_coro = coro
        self._close_coro_args = args

    # Return current state of switch (0 = pressed)
    def __call__(self):
        return self.switchstate

    async def switchcheck(self):
        loop = self.loop
        while True:
            state = self.pin.value()
            if state != self.switchstate:
                # State has changed: act on it now.
                self.switchstate = state
                if state == 0 and self.close_coro:
                    loop.call_soon(self._close_coro(*self._close_coro_args))
                elif state == 1 and self._open_coro:
                    loop.call_soon(self._open_coro(*self._open_coro_args))
            # Ignore further state changes until switch has settled
            await asyncio.sleep_ms(Switch.debounce_ms)

class Pushbutton(object):
    debounce_ms = 50
    long_press_ms = 1000
    double_click_ms = 400
    def __init__(self, pin):
        self.pin = pin # Initialise for input
        self.loop = asyncio.get_event_loop()
        self._true_coro = False
        self._false_coro = False
        self._double_coro = False
        self._long_coro = False
        self.sense = pin.value()  # Convert from electrical to logical value
        self.buttonstate = self.rawstate()  # Initial state
        self.loop.call_soon(self.buttoncheck())  # Thread runs forever

    def true_coro(self, coro, args=()):
        self._true_coro = coro
        self._true_coro_args = args

    def false_coro(self, coro, args=()):
        self._false_coro = coro
        self._false_coro_args = args

    def double_coro(self, coro, args=()):
        self._double_coro = coro
        self._double_coro_args = args

    def long_coro(self, coro, args=()):
        self._long_coro = coro
        self._long_coro_args = args

    # Current non-debounced logical button state: True == pressed
    def rawstate(self):
        return bool(self.pin.value() ^ self.sense)

    # Current debounced state of button (True == pressed)
    def __call__(self):
        return self.buttonstate

    async def buttoncheck(self):
        loop = self.loop
        if self._long_coro:
            longdelay = Delay_ms(self._long_coro, self._long_coro_args)
        if self._double_coro:
            doubledelay = Delay_ms()
        while True:
            state = self.rawstate()
            # State has changed: act on it now.
            if state != self.buttonstate:
                self.buttonstate = state
                if state:
                    # Button is pressed
                    if self._long_coro and not longdelay.running():
                        # Start long press delay
                        longdelay.trigger(Pushbutton.long_press_ms)
                    if self._double_coro:
                        if doubledelay.running():
                            loop.call_soon(self._double_coro(*self._double_coro_args))
                        else:
                            # First click: start doubleclick timer
                            doubledelay.trigger(Pushbutton.double_click_ms)
                    if self._true_coro:
                        loop.call_soon(self._true_coro(*self._true_coro_args))
                else:
                    # Button release
                    if self._long_coro and longdelay.running():
                        # Avoid interpreting a second click as a long push
                        longdelay.stop()
                    if self._false_coro:
                        loop.call_soon(self._false_coro(*self._false_coro_args))
            # Ignore state changes until switch has settled
            await asyncio.sleep_ms(Pushbutton.debounce_ms)
