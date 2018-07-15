# rtc_time.py Pyboard-only RTC based timing for low power uasyncio
# Author: Peter Hinch
# Copyright Peter Hinch 2018 Released under the MIT license

# Code based on extmod/utime_mphal.c
# millisecs roll over on 7 days rather than 12.42757 days

# If not running on a Pyboard the normal utime timebase is used. This is also
# used on a USB connected Pyboard to keep the USB connection open.
# On an externally powered Pyboard an RTC timebase is substituted.

import sys

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
        if pyb.Pin.board.USB_VBUS.value() == 1:  # USB physically connected
            print('USB connection: rtc_time disabled.')
        else:
            pyb.usb_mode(None)  # Save power
            use_utime = False  # use RTC timebase
else:
    print('rtc_time.py is Pyboard-specific.')

if use_utime:  # Run utime: Pyboard connected to PC via USB or alien platform
    import utime
    ticks_ms = utime.ticks_ms
    ticks_add = utime.ticks_add
    ticks_diff = utime.ticks_diff
    sleep_ms = utime.sleep_ms
    lo_power = lambda _ : (yield)
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

    # This function is unused by uasyncio as its only call is in core.wait which
    # is overridden in __init__.py. This means that the lo_power coro can rely
    # on rtc.wakeup()
    def sleep_ms(t):
        end = ticks_add(ticks_ms(), t)
        while t > 0:
            if t < 9:  # <= 2 RTC increments
                pyb.delay(t)  # Just wait and quit
                break
            rtc.wakeup(t)
            pyb.stop()  # Note some interrupt might end this prematurely
            rtc.wakeup(None)
            t = ticks_diff(end, ticks_ms())

    def lo_power(t_ms):
        rtc.wakeup(t_ms)
        while True:
            pyb.stop()
            yield
