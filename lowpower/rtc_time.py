# rtc_time.py Pyboard-only RTC based timing for low power uasyncio
# Author: Peter Hinch
# Copyright Peter Hinch 2018-2019 Released under the MIT license

# Code based on extmod/utime_mphal.c
# millisecs roll over on 7 days rather than 12.42757 days

# If not running on a Pyboard the normal utime timebase is used. This is also
# used on a USB connected Pyboard to keep the USB connection open.
# On an externally powered Pyboard an RTC timebase is substituted.

import sys
import utime
from os import uname
from rtc_time_cfg import enabled, disable_3v3, disable_leds, disable_pins

if not enabled:  # uasyncio traps this and uses utime
    raise ImportError('rtc_time is not enabled.')

# sleep_ms is defined to stop things breaking if someone imports uasyncio.core
# Power won't be saved if this is done.
sleep_ms = utime.sleep_ms

d_series = uname().machine[:4] == 'PYBD'
use_utime = True  # Assume the normal utime timebase

if sys.platform == 'pyboard':
    import pyb
    mode = pyb.usb_mode()
    if mode is None:  # USB is disabled
        use_utime = False  # use RTC timebase
    elif 'VCP' in mode:  # User has enabled VCP in boot.py
        # Detect an active connection (not just a power source)
        if pyb.USB_VCP().isconnected():  # USB will work normally
            print('USB connection: rtc_time disabled.')
        else:
            pyb.usb_mode(None)  # Save power
            use_utime = False  # use RTC timebase
else:
    raise OSError('rtc_time.py is Pyboard-specific.')

# For lowest power consumption set unused pins as inputs with pullups.
# Note the 4K7 I2C pullups on X9 X10 Y9 Y10 (Pyboard 1.x).

# Pulling Pyboard D pins should be disabled if using WiFi as it now seems to
# interfere with it. Although until issue #5152 is fixed it's broken anyway.
if d_series:
    print('Running on Pyboard D')
    if not use_utime:
        def low_power_pins():
            pins = [
                # user IO pins
                'A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10', 'A11', 'A12', 'A13', 'A14', 'A15',
                'B0', 'B1', 'B3', 'B4', 'B5', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12', 'B13',
                'C0', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6',
                'D0', 'D3', 'D8', 'D9',
                'E0', 'E1', 'E12', 'E14', 'E15',
                'F1', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F13', 'F14', 'F15',
                'H2', 'H3', 'H5', 'H6', 'H7', 'H8',
                'I0', 'I1',

                # internal pins
                'D1', 'D14', 'D15',
                'F0', 'F12',
                'G0', 'G1', 'G2', 'G3', 'G4', 'G5', #'G6',
                'H4', 'H9', 'H10', 'H11', 'H12', 'H13', 'H14', 'H15',
                'I2', 'I3',
            ]
            pins_led = ['F3', 'F4', 'F5',]
            pins_sdmmc = ['D6', 'D7', 'G9', 'G10', 'G11', 'G12']
            pins_wlan = ['D2', 'D4', 'I7', 'I8', 'I9', 'I11']
            pins_bt = ['D5', 'D10', 'E3', 'E4', 'E5', 'E6', 'G8', 'G13', 'G14', 'G15', 'I4', 'I5', 'I6', 'I10']
            pins_qspi1 = ['B2', 'B6', 'D11', 'D12', 'D13', 'E2']
            pins_qspi2 = ['E7', 'E8', 'E9', 'E10', 'E11', 'E13']
            if disable_pins:
                for p in pins:
                    pyb.Pin(p, pyb.Pin.IN, pyb.Pin.PULL_DOWN)
            if disable_3v3:
                pyb.Pin('EN_3V3', pyb.Pin.IN, None)
            if disable_leds:
                for p in pins_led:
                    pyb.Pin(p, pyb.Pin.IN, pyb.Pin.PULL_UP)
        low_power_pins()
else:
    print('Running on Pyboard 1.x')
    for pin in [p for p in dir(pyb.Pin.board) if p[0] in 'XY']:
        pin_x = pyb.Pin(pin, pyb.Pin.IN, pyb.Pin.PULL_UP)
# User code redefines any pins in use

if use_utime:
    ticks_ms = utime.ticks_ms
    ticks_add = utime.ticks_add
    ticks_diff = utime.ticks_diff
else:   # All conditions met for low power operation
    _PERIOD = const(604800000)  # ms in 7 days
    _PERIOD_2 = const(302400000)  # half period
    _SS_TO_MS = 1000/256  # Subsecs to ms
    rtc = pyb.RTC()
    # dt: (year, month, day, weekday, hours, minutes, seconds, subseconds)
    # weekday is 1-7 for Monday through Sunday.
    if d_series:
        # Subseconds are μs
        def ticks_ms():
            dt = rtc.datetime()
            return ((dt[3] - 1)*86400000 + dt[4]*3600000 + dt[5]*60000 + dt[6]*1000 +
                    int(dt[7] / 1000))
    else:
        # subseconds counts down from 255 to 0
        def ticks_ms():
            dt = rtc.datetime()
            return ((dt[3] - 1)*86400000 + dt[4]*3600000 + dt[5]*60000 + dt[6]*1000 +
                    int(_SS_TO_MS * (255 - dt[7])))

    def ticks_add(a, b):
        return (a + b) % _PERIOD

    def ticks_diff(end, start):
        return ((end - start + _PERIOD_2) % _PERIOD) - _PERIOD_2

import uasyncio as asyncio

def functor(cls):
    instance = None
    def getinstance(*args, **kwargs):
        nonlocal instance
        if instance is None:
            instance = cls(*args, **kwargs)
            return instance
        return instance(*args, **kwargs)
    return getinstance

@functor
class Latency:
    def __init__(self, t_ms=100):
        if use_utime:  # Not in low power mode: t_ms stays zero
            self._t_ms = 0
        else:
            if asyncio.got_event_loop():
                self._t_ms = max(t_ms, 0)
                loop = asyncio.get_event_loop()
                loop.create_task(self._run())
            else:
                raise OSError('Event loop not instantiated.')

    def _run(self):
        print('Low power mode is ON.')
        rtc = pyb.RTC()
        rtc.wakeup(self._t_ms)
        t_ms = self._t_ms
        while True:
            if t_ms > 0:
                pyb.stop()
            # Pending tasks run once, may change self._t_ms
            yield
            if t_ms != self._t_ms:  # Has changed: update wakeup
                t_ms = self._t_ms
                if t_ms > 0:
                    rtc.wakeup(t_ms)
                else:
                    rtc.wakeup(None)

    def __call__(self, t_ms=None):
        v = self._t_ms
        if t_ms is not None:
            self._t_ms = max(t_ms, 0)
        return v
