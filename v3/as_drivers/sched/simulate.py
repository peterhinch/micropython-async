# simulate.py Adapt this to simulate scheduled sequences

from time import localtime, mktime
from sched.cron import cron

days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
tim = 0  # Global time in secs

def print_time(msg=""):
    yr, mo, md, h, m, s, wd = localtime(tim)[:7]
    print(f"{msg} {h:02d}:{m:02d}:{s:02d} on {days[wd]} {md:02d}/{mo:02d}/{yr:02d}")

def wait(cr):  # Simulate waiting on a cron instance
    global tim
    tim += 2  # Must always wait >=2s before calling cron again
    dt = cr(tim)
    hrs, m_s = divmod(dt + 2, 3600)  # For neat display add back the 2 secs
    mins, secs = divmod(m_s, 60)
    print(f"Wait {hrs}hrs {mins}mins {secs}s")
    tim += dt
    print_time("Time now:")

def set_time(y, month, mday, hrs, mins, secs):
    global tim
    tim = mktime((y, month, mday, hrs, mins, secs, 0, 0))
    print_time("Start at:")

# Adapt the following to emulate the proposed application. Cron args
# secs=0, mins=0, hrs=3, mday=None, month=None, wday=None

def sim(*args):
    set_time(*args)
    cs = cron(hrs = 0, mins = 59)
    wait(cs)
    cn = cron(wday=(0, 5), hrs=(1, 10), mins = range(0, 60, 15))
    for _ in range(10):
        wait(cn)
        print("Run payload.\n")

sim(2023, 3, 29, 15, 20, 0)  # Start time: year, month, mday, hrs, mins, secs
