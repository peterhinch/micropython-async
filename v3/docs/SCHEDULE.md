# 0. Contents

 1. [Scheduling tasks](./SCHEDULE.md#1-scheduling-tasks)  
 2. [Overview](./SCHEDULE.md#2-overview)  
 3. [Installation](./SCHEDULE.md#3-installation)  
 4. [The cron object](./SCHEDULE.md#4-the-cron-object)  
  4.1 [Time specifiers](./SCHEDULE.md#41-time-specifiers)  
  4.2 [The time to an event](./SCHEDULE.md#42-the-time-to-an-event)  
  4.3 [How it works](./SCHEDULE.md#43-how-it-works)  
  4.4 [Calendar behaviour](./SCHEDULE.md#44-calendar-behaviour)  
  4.5 [Limitations](./SCHEDULE.md#45-limitations)  
  4.6 [The Unix build](./SCHEDULE.md#46-the-unix-build)  
 5. [The schedule function](./SCHEDULE.md#5-the-schedule-function) The primary interface for uasyncio  
 6. [Use in synchronous code](./SCHEDULE.md#6-use-in-synchronous-code) If you really must  
 7. [Hardware timing limitations](./SCHEDULE.md#7-hardware-timing-limitations)  

##### [Tutorial](./TUTORIAL.md#contents)  
##### [Main V3 README](../README.md)

# 1. Scheduling tasks

A common requirement is to schedule tasks to occur at specific times in the
future. This module facilitates this. The module can accept wildcard values
enabling tasks to be scheduled in a flexible manner. For example you might want
a callback to run at 3.10 am on every month which has an "r" in the name.

It is partly inspired by the Unix cron table, also by the
[Python schedule](https://github.com/dbader/schedule) module. Compared to the
latter it is less capable but is small, fast and designed for microcontroller
use. Repetitive and one-shot events may be created.

It is ideally suited for use with `uasyncio` and basic use requires minimal
`uasyncio` knowledge. Users intending only to schedule callbacks can simply
adapt the example code. It can be used in synchronous code and an example is
provided.

It is cross-platform and has been tested on Pyboard, Pyboard D, ESP8266, ESP32
and the Unix build (the latter is subject to a minor local time issue).

# 2. Overview

There are two components, the `cron` object (in `sched/cron.py`) and the
`schedule` function (in `sched/sched.py`). The user creates `cron` instances,
passing arguments specifying time intervals. The `cron` instance may be run at
any time and will return the time in seconds to the next scheduled event.

The `schedule` function is an optional component for use with `uasyncio`. The
function takes a `cron` instance and a callback and causes that callback to run
at the times specified by the `cron`. A coroutine may be substituted for the
callback - at the specified times it will be promoted to a `Task` and run.

##### [Top](./SCHEDULE.md#0-contents)

# 3. Installation

Copy the `sched` directory and contents to the target's filesystem. It requires
`uasyncio` V3 which is included in daily firmware builds. It will be in release
builds after V1.12.

To install to an SD card using [rshell](https://github.com/dhylands/rshell)
move to the parent directory of `sched` and issue:
```
> rsync sched /sd/sched
```
Adapt the destination as appropriate for your hardware.

# 4. The cron object

This is a closure. It accepts a time specification for future events. Each call
returns the number of seconds to wait for the next event to occur.

It takes the following keyword-only args. A flexible set of data types are
accepted. These are known as `Time specifiers` and described below. Valid
numbers are shown as inclusive ranges.
 1. `secs=0` Seconds (0..59).
 2. `mins=0` Minutes (0..59).
 3. `hrs=3` Hours (0..23).
 4. `mday=None` Day of month (1..31).
 5. `month=None` Months (1..12).
 6. `wday=None` Weekday (0..6 Mon..Sun).

##### [Top](./SCHEDULE.md#0-contents)

## 4.1 Time specifiers

The args may be of the following types.
 1. `None` This is a wildcard matching any value. Do not use for `secs`.
 2. An integer.
 3. An object supporting the Python iterator protocol and iterating over
 integers. For example `hrs=(3, 17)` will cause events to occur at 3am and 5pm,
 `wday=range(0, 5)` specifies weekdays. Tuples, lists, ranges or sets may be
 passed.

Legal ranges are listed above. Basic validation is done when a `cron` is
instantiated.

Note the implications of the `None` wildcard. Setting `mins=None` will schedule
the event to occur on every minute (equivalent to `*` in a Unix cron table).
Setting `secs=None` or consecutive seconds values will cause a `ValueError` -
events must be at least two seconds apart.

Default values schedule an event every day at 03.00.00.

## 4.2 The time to an event

When the `cron` instance is run, it must be passed a time value (normally the
time now as returned by `time.time()`). The instance returns the number of
seconds to the first event matching the specifier.

```python
from sched.cron import cron
cron1 = cron(hrs=None, mins=range(0, 60, 15))  # Every 15 minutes of every day
cron2 = cron(mday=25, month=12, hrs=9)  # 9am every Christmas day
cron3 = cron(wday=(0, 4))  # 3am every Monday and Friday
now = int(time.time())  # Unix build returns a float here
tnext = min(cron1(now), cron2(now), cron3(now))  # Seconds until 1st event
```

##### [Top](./SCHEDULE.md#0-contents)

## 4.3 How it works

When a cron instance is run it seeks a future time and date relative to the
passed time value. This will be the soonest matching the specifier. A `cron`
instance is a conventional function and does not store state. Repeated calls
will return the same value if passed the same time value (`now` in the above
example).

## 4.4 Calendar behaviour

Specifying a day in the month which exceeds the length of a specified month
(e.g. `month=(2, 6, 7), mday=30`) will produce a `ValueError`. February is
assumed to have 28 days.

### 4.4.1 Behaviour of mday and wday values

The following describes how to schedule something for (say) the second Sunday
in a month, plus limitations of doing this.

If a month is specified which differs from the current month, the day in the
month defaults to the 1st. This can be overridden with `mday` and `wday`, so
you can specify the 21st (`mday=21`) or the first Sunday in the month
(`wday=6`). If `mday` and `wday` are both specified, `mday` is applied first.
This enables the Nth instance of a day to be defined. To specify the second
Sunday in the month specify `mday=8` to skip the first week, and set `wday=6`
to specify Sunday. Unfortunately you can't specify the last (say) Tuesday in
the month.

Specifying `wday=d` and `mday=n` where n > 22 could result in a day beyond the
end of the month. It's not obvious what constitutes rational behaviour in this
pathological corner case: a `ValueError` will result.

### 4.4.2 Time causing month rollover

The following describes behaviour which I consider correct.

On the last day of the month there are circumstances where a time specifier can
cause a day rollover. Consider application start. If a `cron` is run whose time
specifier provides only times prior to the current time, its month increments
and the day changes to the 1st. This is the soonest that the event can occur at
the specified time.

Consider the case where the next month is disallowed. In this case the month
will change to the next valid month. This code, run at 9am on 31st July, would
aim to run the event at 1.59 on 1st October.
```python
my_cron(month=(2, 7, 10), hrs=1, mins=59)  # moves forward 1 day
t_wait = my_cron(time.time())  # but month may be disallowed
```

##### [Top](./SCHEDULE.md#0-contents)

## 4.5 Limitations

The `cron` code has a resolution of 1 second. It is intended for scheduling
infrequent events (`uasyncio` is recommended for doing fast scheduling).

Specifying `secs=None` will cause a `ValueError`. The minimum interval between
scheduled events is 2 seconds. Attempts to schedule events with a shorter gap
will raise a `ValueError`.

A `cron` call typically takes 270 to 520μs on a Pyboard, but the upper bound
depends on the complexity of the time specifiers.

On hardware platforms the MicroPython `time` module does not handle daylight
saving time. Scheduled times are relative to system time. This does not apply
to the Unix build.

## 4.6 The Unix build

Asynchronous use requires `uasyncio` V3, so ensure this is installed on a Linux
box.

The synchronous and asynchronous demos run under the Unix build: it should be
usable on Linux provided the daylight saving time (DST) constraints below are
met.

A consequence of DST is that there are impossible times when clocks go forward
and duplicates when they go back. Scheduling those times will fail. A solution
is to avoid scheduling the times in your region where this occurs (01.00.00 to
02.00.00 in March and October here).

The `crontest.py` test program produces failures under Unix. Most of these
result from the fact that the Unix `localtime` function handles daylight saving
time. On bare hardware MicroPython has no provision for DST. I do not plan to
adapt `cron.py` to account for this: its design focus is small lightweight code
to run on bare metal targets. I could adapt `crontest.py` but it would surely
fail in other countries.

##### [Top](./SCHEDULE.md#0-contents)

# 5. The schedule function

This enables a callback or coroutine to be run at intervals specified by a
`cron` instance. An option for one-shot use is available. It is an asynchronous
function. Positional args:
 1. `fcron` A `cron` instance.
 2. `routine` The callable (callback or coroutine) to run.
 3. `args=()` A tuple of args for the callable.
 4. `run_once=False` If `True` the callable will be run once only.

The `schedule` function only terminates if `run_once=True`, and then typically
after a long time. Usually `schedule` is started with `asyncio.create_task`, as
in the following example where a callback is scheduled at various times. The
code below may be run by issuing
```python
import sched.asynctest
```
This is the demo code.
```python
import uasyncio as asyncio
from sched.sched import schedule
from sched.cron import cron
from time import localtime

def foo(txt):  # Demonstrate callback
    yr, mo, md, h, m, s, wd = localtime()[:7]
    fst = 'Callback {} {:02d}:{:02d}:{:02d} on {:02d}/{:02d}/{:02d}'
    print(fst.format(txt, h, m, s, md, mo, yr))

async def bar(txt):  # Demonstrate coro launch
    yr, mo, md, h, m, s, wd = localtime()[:7]
    fst = 'Coroutine {} {:02d}:{:02d}:{:02d} on {:02d}/{:02d}/{:02d}'
    print(fst.format(txt, h, m, s, md, mo, yr))
    await asyncio.sleep(0)

async def main():
    print('Asynchronous test running...')
    cron4 = cron(hrs=None, mins=range(0, 60, 4))
    asyncio.create_task(schedule(cron4, foo, ('every 4 mins',)))

    cron5 = cron(hrs=None, mins=range(0, 60, 5))
    asyncio.create_task(schedule(cron5, foo, ('every 5 mins',)))

    cron3 = cron(hrs=None, mins=range(0, 60, 3))  # Launch a coroutine
    asyncio.create_task(schedule(cron3, bar, ('every 3 mins',)))

    cron2 = cron(hrs=None, mins=range(0, 60, 2))
    asyncio.create_task(schedule(cron2, foo, ('one shot',), True))
    await asyncio.sleep(900)  # Quit after 15 minutes

try:
    asyncio.run(main())
finally:
    _ = asyncio.new_event_loop()
```

##### [Top](./SCHEDULE.md#0-contents)

# 6. Use in synchronous code

It is possible to use the `cron` closure in synchronous code. This involves
writing an event loop, an example of which is illustrated below. In this
example a task list entry is a tuple with the following contents.
 1. The `cron` instance.
 2. The callback to run.
 3. A tuple of arguments for the callback.
 4. A boolean, `True` if the callback is to be run once only.
 5. A boolean, `True` if the task has been put on the pending queue.

The code below may be found in `sched/synctest.py` and may be run by issuing
```python
import sched.synctest
```
This is the demo code.
```python
from .cron import cron
from time import localtime, sleep, time

def foo(txt):
    yr, mo, md, h, m, s, wd = localtime()[:7]
    fst = "{} {:02d}:{:02d}:{:02d} on {:02d}/{:02d}/{:02d}"
    print(fst.format(txt, h, m, s, md, mo, yr))

def main():
    print('Synchronous test running...')
    tasks = []  # Entries: cron, callback, args, one_shot
    cron4 = cron(hrs=None, mins=range(0, 60, 4))
    tasks.append([cron4, foo, ('every 4 mins',), False, False])
    cron5 = cron(hrs=None, mins=range(0, 60, 5))
    tasks.append([cron5, foo, ('every 5 mins',), False, False])
    cron3 = cron(hrs=None, mins=range(0, 60, 3))
    tasks.append([cron3, foo, ('every 3 mins',), False, False])
    cron2 = cron(hrs=None, mins=range(0, 60, 2))
    tasks.append([cron2, foo, ('one shot',), True, False])
    to_run = []
    while True:
        now = time()  # Ensure constant: get once per iteration.
        tasks.sort(key=lambda x:x[0](now))
        to_run.clear()  # Pending tasks
        deltat = tasks[0][0](now)  # Time to pending task(s)
        for task in (t for t in tasks if t[0](now) == deltat):  # Tasks with same delta t
            to_run.append(task)
            task[4] = True  # Has been scheduled
        # Remove on-shot tasks which have been scheduled
        tasks = [t for t in tasks if not (t[3] and t[4])]
        sleep(deltat)
        for tsk in to_run:
            tsk[1](*tsk[2])
        sleep(2)  # Ensure seconds have rolled over

main()
```

In my opinion the asynchronous version is cleaner and easier to understand. It
is also more versatile because the advanced features of `uasyncio` are
available to the application. The above code is incompatible with `uasyncio`
because of the blocking calls to `time.sleep`.

##### [Top](./SCHEDULE.md#0-contents)

# 7. Hardware timing limitations

The code has been tested on Pyboard 1.x, Pyboard D, ESP32 and ESP8266. All
except ESP8266 have good timing performance. Pyboards can be calibrated to
timepiece precision using a cheap DS3231 and
[this utility](https://github.com/peterhinch/micropython-samples/tree/master/DS3231).

The ESP8266 has poor time stability so is not well suited to long term timing
applications. On my reference board timing drifted by 1.4mins/hr, an error of
2.3%.

Boards with internet connectivity can periodically synchronise to an NTP server
but this carries a risk of sudden jumps in the system time which may disrupt
`uasyncio` and the scheduler.

##### [Top](./SCHEDULE.md#0-contents)
