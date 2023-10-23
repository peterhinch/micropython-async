# sw_array.py A crosspoint array of pushbuttons

# Copyright (c) 2023 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import asyncio
from . import RingbufQueue
from time import ticks_ms, ticks_diff

# A crosspoint array of pushbuttons
# Tuples/lists of pins. Rows are OUT, cols are IN
class Keyboard(RingbufQueue):
    def __init__(self, rowpins, colpins, *, bufsize=10, db_delay=50):
        super().__init__(bytearray(bufsize) if isinstance(bufsize, int) else bufsize)
        self.rowpins = rowpins
        self.colpins = colpins
        self._state = 0  # State of all keys as bitmap
        for opin in self.rowpins:  # Initialise output pins
            opin(1)
        self._run = asyncio.create_task(self.scan(len(rowpins) * len(colpins), db_delay))

    def __getitem__(self, scan_code):
        return bool(self._state & (1 << scan_code))

    async def scan(self, nkeys, db_delay):
        while True:
            cur = 0  # Current bitmap of logical key states
            for opin in self.rowpins:
                opin(0)  # Assert output
                for ipin in self.colpins:
                    cur <<= 1
                    cur |= ipin() ^ 1  # Convert physical to logical
                opin(1)
            if pressed := (cur & ~self._state):  # 1's are newly pressed button(s)
                for sc in range(nkeys):
                    if pressed & 1:
                        try:
                            self.put_nowait(sc)
                        except IndexError:  # q full. Overwrite oldest
                            pass
                    pressed >>= 1
            changed = cur ^ self._state  # Any new press or release
            self._state = cur
            await asyncio.sleep_ms(db_delay if changed else 0)  # Wait out bounce

    def deinit(self):
        self._run.cancel()


CLOSE = const(1)  # cfg comprises the OR of these constants
OPEN = const(2)
LONG = const(4)
DOUBLE = const(8)
SUPPRESS = const(16)  # Disambiguate: see docs.

# Entries in queue are (scan_code, event) where event is an OR of above constants.
# rowpins/colpins are tuples/lists of pins. Rows are OUT, cols are IN.
# cfg is a logical OR of above constants. If a bit is 0 that state will never be reported.
class SwArray(RingbufQueue):
    debounce_ms = 50  # Attributes can be varied by user
    long_press_ms = 1000
    double_click_ms = 400

    def __init__(self, rowpins, colpins, cfg, *, bufsize=10):
        super().__init__(bufsize)
        self._rowpins = rowpins
        self._colpins = colpins
        self._cfg = cfg
        self._state = 0  # State of all buttons as bitmap
        self._flags = 0  # Busy bitmap
        self._basic = not bool(cfg & (SUPPRESS | LONG | DOUBLE))  # Basic mode
        self._suppress = bool(cfg & SUPPRESS)
        for opin in self._rowpins:  # Initialise output pins
            opin(1)  # open circuit
        self._run = asyncio.create_task(self._scan(len(rowpins) * len(colpins)))

    def __getitem__(self, scan_code):
        return bool(self._state & (1 << scan_code))

    def _put(self, sc, evt):
        if evt & self._cfg:  # Only if user has requested it
            try:
                self.put_nowait((sc, evt))
            except IndexError:  # q full. Overwrite oldest
                pass

    def _timeout(self, ts, condition):
        t = SwArray.long_press_ms if condition == LONG else SwArray.double_click_ms
        return ticks_diff(ticks_ms(), ts) > t

    def _busy(self, sc, v):
        of = self._flags  # Return prior state
        if v:
            self._flags |= 1 << sc
        else:
            self._flags &= ~(1 << sc)
        return (of >> sc) & 1

    async def _finish(self, sc):  # Tidy up. If necessary await a contact open
        while self[sc]:
            await asyncio.sleep_ms(0)
        self._put(sc, OPEN)
        self._busy(sc, False)

    def keymap(self):  # Return a bitmap of debounced state of all buttons/switches
        return self._state

    # Handle long, double. Switch has closed.
    async def _defer(self, sc):
        # Wait for contact closure to be registered: let calling loop complete
        await asyncio.sleep_ms(0)
        ts = ticks_ms()
        if not self._suppress:
            self._put(sc, CLOSE)
        while self[sc]:  # Pressed
            await asyncio.sleep_ms(0)
            if self._timeout(ts, LONG):
                self._put(sc, LONG)
                await self._finish(sc)
                return
        if not self._suppress:
            self._put(sc, OPEN)
        while not self[sc]:
            await asyncio.sleep_ms(0)
            if self._timeout(ts, DOUBLE):  # No second closure
                self._put(sc, CLOSE)  # Single press. Report CLOSE
                await self._finish(sc)  # then OPEN
                return
        self._put(sc, DOUBLE)
        await self._finish(sc)

    async def _scan(self, nkeys):
        db_delay = SwArray.debounce_ms
        while True:
            cur = 0  # Current bitmap of logical button states (1 == pressed)
            for opin in self._rowpins:
                opin(0)  # Assert output
                for ipin in self._colpins:
                    cur <<= 1
                    cur |= ipin() ^ 1  # Convert physical to logical
                opin(1)
            curb = cur  # Copy current bitmap
            if changed := (cur ^ self._state):  # 1's are newly canged button(s)
                for sc in range(nkeys):
                    if changed & 1:  # Current button has changed state
                        if self._basic:  # No timed behaviour
                            self._put(sc, CLOSE if cur & 1 else OPEN)
                        elif cur & 1:  # Closed
                            if not self._busy(sc, True):  # Currently not busy
                                asyncio.create_task(self._defer(sc))  # Q is handled asynchronously
                    changed >>= 1
                    cur >>= 1
            changed = curb ^ self._state  # Any new press or release
            self._state = curb
            await asyncio.sleep_ms(db_delay if changed else 0)  # Wait out bounce

    def deinit(self):
        self._run.cancel()
