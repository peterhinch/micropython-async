# crontest.py

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

from time import time, ticks_diff, ticks_us, localtime
from sched.cron import cron
import sys

maxruntime = 0
fail = 0
def result(t, msg):
    global fail
    if t != next(iexp):
        print('FAIL', msg, t)
        fail += 1
        return
    print('PASS', msg, t)

def test(*, secs=0, mins=0, hrs=3, mday=None, month=None, wday=None, tsource=None):
    global maxruntime
    ts = int(time() if tsource is None else tsource)  # int() for Unix build
    cg = cron(secs=secs, mins=mins, hrs=hrs, mday=mday, month=month, wday=wday)
    start = ticks_us()
    t = cg(ts)  # Time relative to ts
    delta = ticks_diff(ticks_us(), start)
    maxruntime = max(maxruntime, delta)
    print('Runtime = {}μs'.format(delta))
    tev = t + ts  # Absolute time of 1st event
    yr, mo, md, h, m, s, wd = localtime(tev)[:7]
    print('{:02d}:{:02d}:{:02d} on {:02d}/{:02d}/{:02d}'.format(h, m, s, md, mo, yr))
    return t  # Relative time

now = 1596074400 if sys.platform == 'linux' else 649393200  # 3am Thursday (day 3) 30 July 2020
iexp = iter([79500, 79500, 86700, 10680, 13564800, 17712000,
             12781800, 11217915, 5443200, 21600, 17193600,
             18403200, 5353140, 13392000, 18662400])
# Expect 01:05:00 on 31/07/2020
result(test(wday=4, hrs=(1,2), mins=5, tsource=now), 'wday and time both cause 1 day increment.')
# 01:05:00 on 31/07/2020
result(test(hrs=(1,2), mins=5, tsource=now), 'time causes 1 day increment.')
# 03:05:00 on 31/07/2020
result(test(wday=4, mins=5, tsource=now), 'wday causes 1 day increment.')
# 05:58:00 on 30/07/2020
result(test(hrs=(5, 23), mins=58, tsource=now), 'time increment no day change.')
# 03:00:00 on 03/01/2021
result(test(month=1, wday=6, tsource=now), 'month and year rollover, 1st Sunday')
# 03:00:00 on 20/02/2021
result(test(month=2, mday=20, tsource=now), 'month and year rollover, mday->20 Feb')
# 01:30:00 on 25/12/2020
result(test(month=12, mday=25, hrs=1, mins=30, tsource=now), 'Forward to Christmas day, hrs backwards')
# 23:05:15 on 06/12/2020
result(test(month=12, wday=6, hrs=23, mins=5, secs=15, tsource=now), '1st Sunday in Dec 2020')
# 03:00:00 on 01/10/2020
result(test(month=10, tsource=now), 'Current time on 1st Oct 2020')
# 09:00:00 on 30/07/2020
result(test(month=7, hrs=9, tsource=now), 'Explicitly specify current month')
# 03:00:00 on 14/02/2021
result(test(month=2, mday=8, wday=6, tsource=now), 'Second Sunday in February 2021')
# 03:00:00 on 28/02/2021
result(test(month=2, mday=22, wday=6, tsource=now), 'Fourth Sunday in February 2021')  # last day of month
# 01:59:00 on 01/10/2020
result(test(month=(7, 10), hrs=1, mins=59, tsource=now + 24*3600), 'Time causes month rollover to next legal month')
# 03:00:00 on 01/01/2021
result(test(month=(7, 1), mday=1, tsource=now), 'mday causes month rollover to next year')
# 03:00:00 on 03/03/2021
result(test(month=(7, 3), wday=(2, 6), tsource=now), 'wday causes month rollover to next year')
print('Max runtime {}μs'.format(maxruntime))
if fail:
    print(fail, 'FAILURES OCCURRED')
else:
    print('ALL TESTS PASSED')
