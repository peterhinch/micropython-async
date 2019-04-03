# rtc_time.py Pyboard-only RTC based timing for low power uasyncio
# Author: Peter Hinch
# Copyright Peter Hinch 2018 Released under the MIT license

# Code based on extmod/utime_mphal.c
# millisecs roll over on 7 days rather than 12.42757 days

# If not running on a Pyboard the normal utime timebase is used. This is also
# used on a USB connected Pyboard to keep the USB connection open.
# On an externally powered Pyboard an RTC timebase is substituted.

import sys
import utime

_PERIOD = const(604800000)  # ms in 7 days
_PERIOD_2 = const(302400000)  # half period
_SS_TO_MS = 1000/256  # Subsecs to ms

use_utime = True  # Assume the normal utime timebase
if sys.platform == 'pyboard':
    import pyb
    mode = pyb.usb_mode()
    if mode is None:  # USB is disabled
        use_utime = False  # use RTC timebase
    elif 'VCP' in mode:  # User has enabled VCP in boot.py
        usb_conn = pyb.Pin.board.USB_VBUS.value()  # USB physically connected to pyb V1.x
        if not usb_conn:
            usb_conn = hasattr(pyb.Pin.board, 'USB_HS_DP') and pyb.Pin.board.USB_HS_DP.value()
        if not usb_conn:
            usb_conn = hasattr(pyb.Pin.board, 'USB_DP') and pyb.Pin.board.USB_DP.value()
        if usb_conn:
            print('USB connection: rtc_time disabled.')
        else:
            pyb.usb_mode(None)  # Save power
            use_utime = False  # use RTC timebase
else:
    raise OSError('rtc_time.py is Pyboard-specific.')

# For lowest power consumption set unused pins as inputs with pullups.
# Note the 4K7 I2C pullups on X9 X10 Y9 Y10.
for pin in [p for p in dir(pyb.Pin.board) if p[0] in 'XY']:
    pin_x = pyb.Pin(pin, pyb.Pin.IN, pyb.Pin.PULL_UP)
# User code redefines any pins in use

import uasyncio as asyncio

# Common version has a needless dict: https://www.python.org/dev/peps/pep-0318/#examples
# https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
# Resolved: https://forum.micropython.org/viewtopic.php?f=2&t=5033&p=28824#p28824
def singleton(cls):
    instance = None
    def getinstance(*args, **kwargs):
        nonlocal instance
        if instance is None:
            instance = cls(*args, **kwargs)
        return instance
    return getinstance

@singleton
class Latency():
    def __init__(self, t_ms=100):
        if use_utime:  # Not in low power mode: t_ms stays zero
            self._t_ms = 0
        else:
            if asyncio.got_event_loop():
                self._t_ms = t_ms
                loop = asyncio.get_event_loop()
                loop.create_task(self._run())
            else:
                raise OSError('Event loop not instantiated.')

    def _run(self):
        rtc = pyb.RTC()
        rtc.wakeup(self._t_ms)
        t_ms = self._t_ms
        while True:
            if t_ms > 0:
                pyb.stop()
            yield
            if t_ms != self._t_ms:
                t_ms = self._t_ms
                if t_ms > 0:
                    rtc.wakeup(t_ms)
                else:
                    rtc.wakeup(None)

    def value(self, val=None):
        if val is not None and not use_utime:
            self._t_ms = max(val, 0)
        return self._t_ms

# sleep_ms is defined to stop things breaking if someone imports uasyncio.core
# Power won't be saved if this is done.
sleep_ms = utime.sleep_ms
if use_utime:  # Run utime: Pyboard connected to PC via USB or alien platform
    ticks_ms = utime.ticks_ms
    ticks_add = utime.ticks_add
    ticks_diff = utime.ticks_diff
else:
    rtc = pyb.RTC()
    # dt: (year, month, day, weekday, hours, minutes, seconds, subseconds)
    # weekday is 1-7 for Monday through Sunday.
    # subseconds counts down from 255 to 0
    def ticks_ms():
        dt = rtc.datetime()
        return ((dt[3] - 1)*86400000 + dt[4]*3600000 + dt[5]*60000 + dt[6]*1000 +
                int(_SS_TO_MS * (255 - dt[7])))

    def ticks_add(a, b):
        return (a + b) % _PERIOD

    def ticks_diff(end, start):
        return ((end - start + _PERIOD_2) % _PERIOD) - _PERIOD_2
