# aswitch.py Switch and pushbutton classes for asyncio
# Delay_ms A retriggerable delay class. Can schedule a coroutine on timeout.
# Switch Simple debounced switch class for normally open grounded switch.

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

class Delay_ms(object):
    def __init__(self, loop, coro=None, coro_args=()):
        self.loop = loop
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
            loop.call_soon(self.coro(loop, *self.coro_args))
        self._running = False


class Switch(object):
    DEBOUNCETIME = 50
    def __init__(self, loop, pin, close_func=None, close_func_args=(),
                 open_func=None, open_func_args=()):
        self.loop = loop
        self.pin = pin # Should be initialised for input with pullup
        self.close_func = close_func
        self.close_func_args = close_func_args
        self.open_func = open_func
        self.open_func_args = open_func_args
        self.switchstate = self.pin.value()  # Get initial state
        loop.call_soon(self.switchcheck())  # Thread runs forever

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
                if state == 0 and self.close_func:
                    loop.call_soon(self.close_func(loop, *self.close_func_args))
                elif state == 1 and self.open_func:
                    loop.call_soon(self.open_func(loop, *self.open_func_args))
            # Ignore further state changes until switch has settled
            await asyncio.sleep_ms(Switch.DEBOUNCETIME)

class Pushbutton(object):
    DEBOUNCETIME = 50
    LONG_PRESS_MS = 1000
    DOUBLE_CLICK_MS = 400
    def __init__(self, loop, pin,
            true_func = None, true_func_args = (),
            false_func = None, false_func_args = (),
            long_func = None, long_func_args = (),
            double_func = None, double_func_args =()):
        self.pin = pin # Initialise for input
        self.loop = loop
        self.true_func = true_func
        self.true_func_args = true_func_args
        self.false_func = false_func
        self.false_func_args = false_func_args
        self.long_func = long_func
        self.long_func_args = long_func_args
        self.double_func = double_func
        self.double_func_args = double_func_args
        self.sense = pin.value()  # Convert from electrical to logical value
        self.buttonstate = self.rawstate()  # Initial state
        loop.call_soon(self.buttoncheck())  # Thread runs forever

    # Current non-debounced logical button state: True == pressed
    def rawstate(self):
        return bool(self.pin.value() ^ self.sense)

    # Current debounced state of button (True == pressed)
    def __call__(self):
        return self.buttonstate

    async def buttoncheck(self):
        loop = self.loop
        if self.long_func:
            longdelay = Delay_ms(loop, self.long_func, self.long_func_args)
        if self.double_func:
            doubledelay = Delay_ms(loop)
        while True:
            state = self.rawstate()
            # State has changed: act on it now.
            if state != self.buttonstate:
                self.buttonstate = state
                if state:
                    # Button is pressed
                    if self.long_func and not longdelay.running():
                        # Start long press delay
                        longdelay.trigger(Pushbutton.LONG_PRESS_MS)
                    if self.double_func:
                        if doubledelay.running():
                            loop.call_soon(self.double_func(loop, *self.double_func_args))
                        else:
                            # First click: start doubleclick timer
                            doubledelay.trigger(Pushbutton.DOUBLE_CLICK_MS)
                    if self.true_func:
                        loop.call_soon(self.true_func(loop, *self.true_func_args))
                else:
                    # Button release
                    if self.long_func and longdelay.running():
                        # Avoid interpreting a second click as a long push
                        longdelay.stop()
                    if self.false_func:
                        loop.call_soon(self.false_func(loop, *self.false_func_args))
            # Ignore state changes until switch has settled
            await asyncio.sleep_ms(Pushbutton.DEBOUNCETIME)


