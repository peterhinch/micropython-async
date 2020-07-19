# 0. Contents

 1. [Scheduling tasks](./SCHEDULE.md#1-scheduling-tasks)  
 2. [Overview](./SCHEDULE.md#2-overview)  
 3. [Installation](./SCHEDULE.md#3-installation)  
 4. [The schedule function](./SCHEDULE.md#4-the-schedule-function) The primary interface for uasyncio  
  4.1 [Time specifiers](./SCHEDULE.md#41-time-specifiers)  
  4.2 [Calendar behaviour](./SCHEDULE.md#42-calendar-behaviour) Calendars can be tricky...  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.2.1 [Behaviour of mday and wday values](./SCHEDULE.md#421-behaviour-of-mday-and-wday-values)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.2.2 [Time causing month rollover](./SCHEDULE.md#422-time-causing-month-rollover)  
  4.3 [Limitations](./SCHEDULE.md#43-limitations)  
  4.4 [The Unix build](./SCHEDULE.md#44-the-unix-build)  
 5. [The cron object](./SCHEDULE.md#5-the-cron-object) For hackers and synchronous coders  
  5.1 [The time to an event](./SCHEDULE.md#51-the-time-to-an-event)  
  5.2 [How it works](./SCHEDULE.md#52-how-it-works)  
 6. [Hardware timing limitations](./SCHEDULE.md#6-hardware-timing-limitations)  
 7. [Use in synchronous code](./SCHEDULE.md#7-use-in-synchronous-code) If you really must  

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

The `schedule` function (`sched/sched.py`) is the interface for use with
`uasyncio`. The function takes a callback and causes that callback to run at
specified times. A coroutine may be substituted for the callback - at the
specified times it will be promoted to a `Task` and run.

The `schedule` function instantiates a `cron` object (in `sched/cron.py`). This
is the core of the scheduler: it is a closure created with a time specifier and
returning the time to the next scheduled event. Users of `uasyncio` do not need
to deal with `cron` instances.

This library can also be used in synchronous code, in which case `cron`
instances must explicitly be created.

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

The following files are installed in the `sched` directory.
 1. `cron.py` Computes time to next event.
 2. `sched.py` The `uasyncio` `schedule` function: schedule a callback or coro.
 3. `primitives/__init__.py` Necessary for `sched.py`.
 4. `asynctest.py` Demo of asynchronous scheduling.
 5. `synctest.py` Synchronous scheduling demo. For `uasyncio` phobics only.
 6. `crontest.py` A test for `cron.py` code.
 7. `__init__.py` Empty file for Python package.

The `crontest` script is only of interest to those wishing to adapt `cron.py`.
To run error-free a bare metal target should be used for the reason discussed
[here](./SCHEDULE.md#46-the-unix-build).

# 4. The schedule function

This enables a callback or coroutine to be run at intervals. The callable can
be specified to run forever, once only or a fixed number of times. `schedule`
is an asynchronous function.

Positional args:
 1. `func` The callable (callback or coroutine) to run.
 2. Any further positional args are passed to the callable.

Keyword-only args. Args 1..6 are
[Time specifiers](./SCHEDULE.md#41-time-specifiers): a variety of data types
may be passed, but all ultimately produce integers (or `None`). Valid numbers
are shown as inclusive ranges.
 1. `secs=0` Seconds (0..59).
 2. `mins=0` Minutes (0..59).
 3. `hrs=3` Hours (0..23).
 4. `mday=None` Day of month (1..31).
 5. `month=None` Months (1..12).
 6. `wday=None` Weekday (0..6 Mon..Sun).
 7. `times=None` If an integer `n` is passed the callable will be run at the
 next `n` scheduled times. Hence a value of 1 specifies a one-shot event.

The `schedule` function only terminates if `times` is not `None`. In this case
termination occurs after the last run of the callable and the return value is
the value returned by that run of the callable.

Because `schedule` does not terminate promptly it is usually started with
`asyncio.create_task`, as in the following example where a callback is
scheduled at various times. The code below may be run by issuing
```python
import sched.asynctest
```
This is the demo code.
```python
import uasyncio as asyncio
from sched.sched import schedule
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
    asyncio.create_task(schedule(foo, 'every 4 mins', hrs=None, mins=range(0, 60, 4)))
    asyncio.create_task(schedule(foo, 'every 5 mins', hrs=None, mins=range(0, 60, 5)))
    # Launch a coroutine
    asyncio.create_task(schedule(bar, 'every 3 mins', hrs=None, mins=range(0, 60, 3)))
    # Launch a one-shot task
    asyncio.create_task(schedule(foo, 'one shot', hrs=None, mins=range(0, 60, 2), times=1))
    await asyncio.sleep(900)  # Quit after 15 minutes

try:
    asyncio.run(main())
finally:
    _ = asyncio.new_event_loop()
```

##### [Top](./SCHEDULE.md#0-contents)

## 4.1 Time specifiers

The args may be of the following types.
 1. `None` This is a wildcard matching any value. Do not use for `secs`.
 2. An integer.
 3. An object supporting the Python iterator protocol and iterating over
 integers. For example `hrs=(3, 17)` will cause events to occur at 3am and 5pm,
 `wday=range(0, 5)` specifies weekdays. Tuples, lists, ranges or sets may be
 passed.

Legal integer values are listed above. Basic validation is done as soon as
`schedule` is run.

Note the implications of the `None` wildcard. Setting `mins=None` will schedule
the event to occur on every minute (equivalent to `*` in a Unix cron table).
Setting `secs=None` or consecutive seconds values will cause a `ValueError` -
events must be at least two seconds apart.

Default values schedule an event every day at 03.00.00.

## 4.2 Calendar behaviour

Specifying a day in the month which exceeds the length of a specified month
(e.g. `month=(2, 6, 7), mday=30`) will produce a `ValueError`. February is
assumed to have 28 days.

### 4.2.1 Behaviour of mday and wday values

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
pathological corner case. Validation will throw a `ValueError` in this case.

### 4.2.2 Time causing month rollover

The following describes behaviour which I consider correct.

On the last day of the month there are circumstances where a time specifier can
cause a day rollover. Consider application start. If a callback is scheduled
with a time specifier offering only times prior to the current time, its month
increments and the day changes to the 1st. This is the soonest that the event
can occur at the specified time.

Consider the case where the next month is disallowed. In this case the month
will change to the next valid month. This code, run at 9am on 31st July, would
aim to run `foo` at 1.59 on 1st October.
```python
asyncio.create_task(schedule(foo, month=(2, 7, 10), hrs=1, mins=59))
```

##### [Top](./SCHEDULE.md#0-contents)

## 4.3 Limitations

The underlying `cron` code has a resolution of 1 second. The library is
intended for scheduling infrequent events (`uasyncio` has its own approach to
fast scheduling).

Specifying `secs=None` will cause a `ValueError`. The minimum interval between
scheduled events is 2 seconds. Attempts to schedule events with a shorter gap
will raise a `ValueError`.

A `cron` call typically takes 270 to 520μs on a Pyboard, but the upper bound
depends on the complexity of the time specifiers.

On hardware platforms the MicroPython `time` module does not handle daylight
saving time. Scheduled times are relative to system time. This does not apply
to the Unix build where daylight saving needs to be considered.

## 4.4 The Unix build

Asynchronous use requires `uasyncio` V3, so ensure this is installed on the
Linux target.

The synchronous and asynchronous demos run under the Unix build. The module is
usable on Linux provided the daylight saving time (DST) constraints below are
met.

A consequence of DST is that there are impossible times when clocks go forward
and duplicates when they go back. Scheduling those times will fail. A solution
is to avoid scheduling the times in your region where this occurs (01.00.00 to
02.00.00 in March and October here).

The `crontest.py` test program produces failures under Unix. These result from
the fact that the Unix `localtime` function handles daylight saving time. The
purpose of `crontest.py` is to check `cron` code. It should be run on bare
metal targets.

##### [Top](./SCHEDULE.md#0-contents)

# 5. The cron object

This is the core of the scheduler. Users of `uasyncio` do not need to concern
themseleves with it. It is documented for those wishing to modify the code and
for those wanting to perform scheduling in synchronous code.

It is a closure whose creation accepts a time specification for future events.
Each subsequent call is passed the current time and returns the number of
seconds to wait for the next event to occur.

It takes the following keyword-only args. A flexible set of data types are
accepted namely [time specifiers](./SCHEDULE.md#41-time-specifiers). Valid
numbers are shown as inclusive ranges.
 1. `secs=0` Seconds (0..59).
 2. `mins=0` Minutes (0..59).
 3. `hrs=3` Hours (0..23).
 4. `mday=None` Day of month (1..31).
 5. `month=None` Months (1..12).
 6. `wday=None` Weekday (0..6 Mon..Sun).

## 5.1 The time to an event

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

## 5.2 How it works

When a cron instance is run it seeks a future time and date relative to the
passed time value. This will be the soonest matching the specifier. A `cron`
instance is a conventional function and does not store state. Repeated calls
will return the same value if passed the same time value (`now` in the above
example).

##### [Top](./SCHEDULE.md#0-contents)

# 6. Hardware timing limitations

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

# 7. Use in synchronous code

It is possible to use the `cron` closure in synchronous code. This involves
the mildly masochistic task of writing an event loop, an example of which is
illustrated below. In this example a task list entry is a tuple with the
following contents.
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
        # Remove one-shot tasks which have been scheduled
        tasks = [t for t in tasks if not (t[3] and t[4])]
        sleep(deltat)
        for tsk in to_run:
            tsk[1](*tsk[2])
        sleep(2)  # Ensure seconds have rolled over

main()
```

In my opinion the asynchronous version is cleaner and easier to understand. It
is also more versatile because the advanced features of `uasyncio` are
available to the application including cancellation of scheduled tasks. The
above code is incompatible with `uasyncio` because of the blocking calls to
`time.sleep()`.

##### [Top](./SCHEDULE.md#0-contents)
