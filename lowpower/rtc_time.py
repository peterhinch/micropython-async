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
from rtc_time_cfg import enabled
if not enabled:
    raise ImportError('rtc_time is not enabled.')

# sleep_ms is defined to stop things breaking if someone imports uasyncio.core
# Power won't be saved if this is done.
sleep_ms = utime.sleep_ms

d_series = uname().machine[:5] == 'PYBD_'
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
if d_series:
    print('Running on Pyboard D')  # Investigate which pins we can do this to TODO
#    pinlist = [p for p in dir(pyb.Pin.board) if p.startswith('W') and p[1].isdigit() and p[-1].isdigit()]
#    sorted(pinlist, key=lambda s: int(s[1:]))
    #pinlist = ['W3', 'W5', 'W6', 'W7', 'W8', 'W9', 'W10', 'W11', 'W12', 'W14', 'W15',
            #'W16', 'W17', 'W18', 'W19', 'W20', 'W22', 'W23', 'W24', 'W25',
            #'W26', 'W27', 'W28', 'W29', 'W30', 'W32', 'W33', 'W34', 'W43', 'W45',
            #'W46', 'W47', 'W49', 'W50', 'W51', 'W52', 'W53', 'W54', 'W55', 'W56',
            #'W57', 'W58', 'W59', 'W60', 'W61', 'W62', 'W63', 'W64', 'W65', 'W66',
            #'W67', 'W68', 'W70', 'W71', 'W72', 'W73', 'W74']
    # sorted([p for p in dir(pyb.Pin.board) if p[0] in 'XY' and p[-1].isdigit()], key=lambda x: int(x[1:]) if x[0]=='X' else int(x[1:])+100)
    pinlist = ['X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8', 'X9', 'X10', 'X11', 'X12',
                'Y3', 'Y4', 'Y5', 'Y6', 'Y7', 'Y8', 'Y9', 'Y10', 'Y11', 'Y12']
    for pin in pinlist:
        pin_x = pyb.Pin(pin, pyb.Pin.IN, pyb.Pin.PULL_UP)
    pyb.Pin('EN_3V3').off()
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
        print('Low power mode is ON.')
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
        v = self._t_ms
        if val is not None:
            self._t_ms = max(val, 0)
        return v
