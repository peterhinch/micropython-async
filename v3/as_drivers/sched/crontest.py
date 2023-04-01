# crontest.py Now works under Unix build

# Copyright (c) 2020-2023 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

from time import time, ticks_diff, ticks_us, localtime, mktime
from sched.cron import cron
import sys

maxruntime = 0
fail = 0

# Args:
# ts Time of run in secs since epoch
# exp Expected absolute end time (yr, mo, md, h, m, s)
# msg Message describing test
# kwargs are args for cron
def test(ts, exp, msg, *, secs=0, mins=0, hrs=3, mday=None, month=None, wday=None):
    global maxruntime, fail
    texp = mktime(exp + (0, 0))  # Expected absolute end time
    yr, mo, md, h, m, s, wd = localtime(texp)[:7]
    print(f"Test: {msg}")
    print(f"Expected endtime:  {h:02d}:{m:02d}:{s:02d} on {md:02d}/{mo:02d}/{yr:02d}")

    cg = cron(secs=secs, mins=mins, hrs=hrs, mday=mday, month=month, wday=wday)
    start = ticks_us()
    t = cg(ts)  # Wait duration returned by cron (secs)
    delta = ticks_diff(ticks_us(), start)
    maxruntime = max(maxruntime, delta)
    yr, mo, md, h, m, s, wd = localtime(t + ts)[:7]  # Get absolute time from cron
    print(f"Endtime from cron: {h:02d}:{m:02d}:{s:02d} on {md:02d}/{mo:02d}/{yr:02d}")
    if t == texp - ts:
        print(f"PASS")
    else:
        print(f"FAIL [{t}]")
        fail += 1
    print(f"Runtime = {delta}us\n")


now = mktime((2020, 7, 30, 3, 0, 0, 0, 0))  # 3am Thursday (day 3) 30 July 2020

exp = (2020, 7, 31, 1, 5, 0)  # Expect 01:05:00 on 31/07/2020
msg = "wday and time both cause 1 day increment."
test(now, exp, msg, wday=4, hrs=(1, 2), mins=5)

exp = (2020, 7, 31, 1, 5, 0)  # 01:05:00 on 31/07/2020
msg = "time causes 1 day increment."
test(now, exp, msg, hrs=(1, 2), mins=5)

exp = (2020, 7, 31, 3, 5, 0)  # 03:05:00 on 31/07/2020
msg = "wday causes 1 day increment."
test(now, exp, msg, wday=4, mins=5)

exp = (2020, 7, 30, 5, 58, 0)  # 05:58:00 on 30/07/2020
msg = "time increment no day change."
test(now, exp, msg, hrs=(5, 23), mins=58)

exp = (2021, 1, 3, 3, 0, 0)  # 03:00:00 on 03/01/2021
msg = "month and year rollover, 1st Sunday"
test(now, exp, msg, month=1, wday=6)

exp = (2021, 2, 20, 3, 0, 0)  # 03:00:00 on 20/02/2021
msg = "month and year rollover, mday->20 Feb"
test(now, exp, msg, month=2, mday=20)

exp = (2020, 12, 25, 1, 30, 0)  # 01:30:00 on 25/12/2020
msg = "Forward to Xmas day, hrs backwards"
test(now, exp, msg, month=12, mday=25, hrs=1, mins=30)

exp = (2020, 12, 6, 23, 5, 15)  # 23:05:15 on 06/12/2020
msg = "1st Sunday in Dec 2020"
test(now, exp, msg, month=12, wday=6, hrs=23, mins=5, secs=15)

exp = (2020, 10, 1, 3, 0, 0)  # 03:00:00 on 01/10/2020
msg = "Current time on 1st Oct 2020"
test(now, exp, msg, month=10)

exp = (2020, 7, 30, 9, 0, 0)  # 09:00:00 on 30/07/2020
msg = "Explicitly specify current month"
test(now, exp, msg, month=7, hrs=9)

exp = (2021, 2, 14, 3, 0, 0)  # 03:00:00 on 14/02/2021
msg = "Second Sunday in February 2021"
test(now, exp, msg, month=2, mday=8, wday=6)

exp = (2021, 2, 28, 3, 0, 0)  # 03:00:00 on 28/02/2021
msg = "Fourth Sunday in February 2021"
test(now, exp, msg, month=2, mday=22, wday=6)  # month end

exp = (2020, 10, 1, 1, 59, 0)  # 01:59:00 on 01/10/2020
msg = "Time causes month rollover to next legal month"
test(now + 24 * 3600, exp, msg, month=(7, 10), hrs=1, mins=59)

exp = (2021, 1, 1, 3, 0, 0)  # 03:00:00 on 01/01/2021
msg = "mday causes month rollover to next year"
test(now, exp, msg, month=(7, 1), mday=1)

exp = (2021, 3, 3, 3, 0, 0)  # 03:00:00 on 03/03/2021
msg = "wday causes month rollover to next year"
test(now, exp, msg, month=(7, 3), wday=(2, 6))

print(f"Max runtime {maxruntime}us")
if fail:
    print(fail, "FAILURES OCCURRED")
else:
    print("ALL TESTS PASSED")
