# esp32_touch.py ESP32 hosts: support Pushbutton based on touch pad.

# Copyright (c) 2026 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

from machine import TouchPad
from . import Pushbutton

class ESP32Touch(Pushbutton):
    thresh = (80 << 8) // 100

    @classmethod
    def threshold(cls, val):
        if not (isinstance(val, int) and 0 < val < 100):
            raise ValueError("Threshold must be in range 1-99")
        cls.thresh = (val << 8) // 100

    def __init__(self, pin, suppress=False):
        self._thresh = 0  # Detection threshold
        self._rawval = 0
        try:
            self._pad = TouchPad(pin)
        except ValueError:
            raise ValueError(pin)  # Let's have a bit of information :)
        super().__init__(pin, suppress, False)

    # Current logical button state: True == touched
    def rawstate(self):
        rv = self._pad.read()  # ~220μs
        if rv > self._rawval:  # Either initialisation or pad was touched
            self._rawval = rv  # when initialised and has now been released
            self._thresh = (rv * ESP32Touch.thresh) >> 8
            return False  # Untouched
        return rv < self._thresh
