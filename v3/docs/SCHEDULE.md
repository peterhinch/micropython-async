# 0. Contents

 1. [Scheduling tasks](./SCHEDULE.md#1-scheduling-tasks)  
 2. [Overview](./SCHEDULE.md#2-overview)  
 3. [Installation](./SCHEDULE.md#3-installation)  
 4. [The schedule coroutine](./SCHEDULE.md#4-the-schedule-coroutine) The primary interface for asyncio.  
  4.1 [Time specifiers](./SCHEDULE.md#41-time-specifiers)  
  4.2 [Calendar behaviour](./SCHEDULE.md#42-calendar-behaviour) Calendars can be tricky...  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.2.1 [Behaviour of mday and wday values](./SCHEDULE.md#421-behaviour-of-mday-and-wday-values)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.2.2 [Time causing month rollover](./SCHEDULE.md#422-time-causing-month-rollover)  
  4.3 [Limitations](./SCHEDULE.md#43-limitations)  
  4.4 [The Unix build](./SCHEDULE.md#44-the-unix-build)  
  4.5 [Callback interface](./SCHEDULE.md#45-callback-interface) Alternative interface using callbacks.  
  4.6 [Event interface](./SCHEDULE.md#46-event-interface) Alternative interface using Event instances.  
5. [The cron object](./SCHEDULE.md#5-the-cron-object) The rest of this doc is for hackers and synchronous coders.   
  5.1 [The time to an event](./SCHEDULE.md#51-the-time-to-an-event)  
  5.2 [How it works](./SCHEDULE.md#52-how-it-works)  
 6. [Hardware timing limitations](./SCHEDULE.md#6-hardware-timing-limitations)  
 7. [Use in synchronous code](./SCHEDULE.md#7-use-in-synchronous-code) If you really must.  
  7.1 [Initialisation](./SCHEDULE.md#71-initialisation)__
 8. [The simulate script](./SCHEDULE.md#8-the-simulate-script) Rapidly test sequences.  
 9. [Daylight saving time](./SCHEDULE.md#9-daylight-saving-time) Notes on timezone and DST when running under an OS.  

Release note:
7th Sep 2024 Document timezone and DST behaviour under Unix build.   
11th Dec 2023 Document astronomy module, allowing scheduling based on Sun and
Moon rise and set times.  
23rd Nov 2023 Add asynchronous iterator interface.  
3rd April 2023 Fix issue #100. Where an iterable is passed to `secs`, triggers
must now be at least 10s apart (formerly 2s).  

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

It is ideally suited for use with `asyncio` and basic use requires minimal
`asyncio` knowledge. Example code is provided offering various ways of
responding to timing triggers including running callbacks. The module can be
also be used in synchronous code and an example is provided.

It is cross-platform and has been tested on Pyboard, Pyboard D, ESP8266, ESP32
and the Unix build.

The `astronomy` module extends this to enable tasks to be scheduled at times
related to Sun and Moon rise and set times. This is documented
[here](https://github.com/peterhinch/micropython-samples/blob/master/astronomy/README.md).

# 2. Overview

The `schedule` coroutine (`sched/sched.py`) is the interface for use with
`asyncio`. Three interface alternatives are offered which vary in the behaviour:
which occurs when a scheduled trigger occurs:
1. An asynchronous iterator is triggered.
2. A user defined `Event` is set.
3. A user defined callback or coroutine is launched.

One or more `schedule` tasks may be assigned to a `Sequence` instance. This
enables an `async for` statement to be triggered whenever any of the `schedule`
tasks is triggered.

Under the hood the `schedule` function instantiates a `cron` object (in
`sched/cron.py`). This is the core of the scheduler: it is a closure created
with a time specifier and returning the time to the next scheduled event. Users
of `asyncio` do not need to deal with `cron` instances. This library can also be
used in synchronous code, in which case `cron` instances must explicitly be
created.

##### [Top](./SCHEDULE.md#0-contents)

# 3. Installation

The `sched` directory and contents must be copied to the target's filesystem.
This may be done with the official
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html):
```bash
$ mpremote mip install "github:peterhinch/micropython-async/v3/as_drivers/sched"
```
On networked platforms it may be installed with [mip](https://docs.micropython.org/en/latest/reference/packages.html).
```py
>>> mip.install("github:peterhinch/micropython-async/v3/as_drivers/sched")
```
Currently these tools install to `/lib` on the built-in Flash memory. To install
to a Pyboard's SD card [rshell](https://github.com/dhylands/rshell) may be used.
Move to `as_drivers` on the PC, run `rshell` and issue:
```
> rsync sched /sd/sched
```

The following files are installed in the `sched` directory.
 1. `cron.py` Computes time to next event.
 2. `sched.py` The `asyncio` `schedule` function: schedule a callback or coro.
 3. `primitives/__init__.py` Necessary for `sched.py`.
 4. `asynctest.py` Demo of asynchronous scheduling.
 5. `synctest.py` Synchronous scheduling demo. For `asyncio` phobics only.
 6. `crontest.py` A test for `cron.py` code.
 7. `simulate.py` A simple script which may be adapted to prove that a `cron`
 instance will behave as expected. See [The simulate script](./SCHEDULE.md#8-the-simulate-script).
 8. `__init__.py` Empty file for Python package.

The `crontest` script is only of interest to those wishing to adapt `cron.py`.
It will run on any MicroPython target.

The [astronomy](https://github.com/peterhinch/micropython-samples/blob/master/astronomy/README.md)
module may be installed with
```bash
$ mpremote mip install "github:peterhinch/micropython-samples/astronomy"
```

# 4. The schedule coroutine

This enables a response to be triggered at intervals. The response can be
specified to occur forever, once only or a fixed number of times. `schedule`
is a coroutine and is typically run as a background task as follows:
```python
asyncio.create_task(schedule(foo, 'every 4 mins', hrs=None, mins=range(0, 60, 4)))
```

Positional args:
 1. `func` This may be a callable (callback or coroutine) to run, a user defined
 `Event` or an instance of a `Sequence`.
 2. Any further positional args are passed to the callable or the `Sequence`;
 these args can be used to enable the triggered object to determine the source
 of the trigger.

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
The event-based interface can be simpler than using callables:

The remainder of this section describes the asynchronous iterator interface as
this is the simplest to use. The other interfaces are discussed in
* [4.5 Callback interface](./SCHEDULE.md#45-callback-interface)
* [4.6 Event interface](./SCHEDULE.md#46-event-interface)

One or more `schedule` instances are collected in a `Sequence` object. This
supports the asynchronous iterator interface:
```python
import asyncio
from sched.sched import schedule, Sequence
from time import localtime

async def main():
    print("Asynchronous test running...")
    seq = Sequence()  # A Sequence comprises one or more schedule instances
    asyncio.create_task(schedule(seq, 'every 4 mins', hrs=None, mins=range(0, 60, 4)))
    asyncio.create_task(schedule(seq, 'every 5 mins', hrs=None, mins=range(0, 60, 5)))
    asyncio.create_task(schedule(seq, 'every 3 mins', hrs=None, mins=range(0, 60, 3)))
    # A one-shot trigger
    asyncio.create_task(schedule(seq, 'one shot', hrs=None, mins=range(0, 60, 2), times=1))
    async for args in seq:
        yr, mo, md, h, m, s, wd = localtime()[:7]
        print(f"Event {h:02d}:{m:02d}:{s:02d} on {md:02d}/{mo:02d}/{yr} args: {args}")

try:
    asyncio.run(main())
finally:
    _ = asyncio.new_event_loop()
```
Note that the asynchronous iterator produces a `tuple` of the args passed to the
`schedule` that triggered it. This enables the code to determine the source of
the trigger.

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
Setting `secs=None` will cause a `ValueError`.

Passing an iterable to `secs` is not recommended: this library is intended for
scheduling relatively long duration events. For rapid sequencing, schedule a
coroutine which awaits `asyncio` `sleep` or `sleep_ms` routines. If an
iterable is passed, triggers must be at least ten seconds apart or a
`ValueError` will result.

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
intended for scheduling infrequent events (`asyncio` has its own approach to
fast scheduling).

Specifying `secs=None` will cause a `ValueError`. The minimum interval between
scheduled events is 2 seconds. Attempts to schedule events with a shorter gap
will raise a `ValueError`.

A `cron` call typically takes 270 to 520μs on a Pyboard, but the upper bound
depends on the complexity of the time specifiers.

On hardware platforms the MicroPython `time` module does not handle daylight
saving time. Scheduled times are relative to system time. Under the Unix build,
where the locale uses daylight saving, its effects should be considered. See
[Daylight saving time](./SCHEDULE.md#9-daylight-saving-time).

## 4.4 The Unix build

Asynchronous use requires `asyncio` V3, so ensure this is installed on the
Linux target. This may be checked with:
```py
import asyncio
asyncio.__version__
```
The module uses local time. When running under an OS, local time is affected by
geographical longitude (timezone - TZ) and daylight saving time (DST). The use
of local time avoids TZ issues but has consequences when the underlying time
source changes due to crossing a DST boundary.

This is explained in detail in [Daylight saving time](./SCHEDULE.md#9-daylight-saving-time).

##### [Top](./SCHEDULE.md#0-contents)

## 4.5 Callback interface

In this instance a user defined `callable` is passed as the first `schedule` arg.
A `callable` may be a function or a coroutine. It is possible for multiple
`schedule` instances to call the same callback, as in the example below. The
code is included in the library as `sched/asyntest.py` and may be run as below.
```python
import sched.asynctest
```
This is the demo code.
```python
import asyncio
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

## 4.6 Event interface

In this instance a user defined `Event` is passed as the first `schedule` arg.
It is possible for multiple `schedule` instances to trigger the same `Event`.
The user is responsible for clearing the `Event`. This interface has a drawback
in that extra positional args passed to `schedule` are lost.
```python
import asyncio
from sched.sched import schedule
from time import localtime

async def main():
    print("Asynchronous test running...")
    evt = asyncio.Event()
    asyncio.create_task(schedule(evt, hrs=10, mins=range(0, 60, 4)))
    while True:
        await evt.wait()  # Multiple tasks may wait on an Event
        evt.clear()  # It must be cleared.
        yr, mo, md, h, m, s, wd = localtime()[:7]
        print(f"Event {h:02d}:{m:02d}:{s:02d} on {md:02d}/{mo:02d}/{yr}")

try:
    asyncio.run(main())
finally:
    _ = asyncio.new_event_loop()
```
See [tutorial](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#32-event).
Also [this doc](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/EVENTS.md)
for a discussion of event-based programming.

##### [Top](./SCHEDULE.md#0-contents)

# 5. The cron object

This is the core of the scheduler. Users of `asyncio` do not need to concern
themseleves with it. It is documented for those wishing to modify the code and
for those wanting to perform scheduling in synchronous code.

It is a closure whose creation accepts a time specification for future
triggers. When called it is passed a time value in seconds since the epoch. It
returns the number of seconds to wait for the next trigger to occur. It stores
no state.

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

The code has been tested on Pyboard 1.x, Pyboard D, RP2, ESP32 and ESP8266. All
except ESP8266 have good timing performance. Pyboards can be calibrated to
timepiece precision using a cheap DS3231 and
[this utility](https://github.com/peterhinch/micropython-samples/tree/master/DS3231).

The ESP8266 has poor time stability so is not well suited to long term timing
applications. On my reference board timing drifted by 1.4mins/hr, an error of
2.3%.

Boards with internet connectivity can periodically synchronise to an NTP server
but this carries a risk of sudden jumps in the system time which may disrupt
`asyncio` and the scheduler.

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
is also more versatile because the advanced features of `asyncio` are
available to the application including cancellation of scheduled tasks. The
above code is incompatible with `asyncio` because of the blocking calls to
`time.sleep()`.

## 7.1 Initialisation

Where a time specifier is an iterator (e.g. `mins=range(0, 60, 15)`) and there
are additional constraints (e.g. `hrs=3`) it may be necessary to delay the
start. The problem is specific to scheduling a sequence at a future time, and
there is a simple solution (which the asynchronous version implements
transparently).

A `cron` object searches forwards from the current time. Assume the above case.
If the code start at 7:05 it picks the first later minute in the `range`,
i.e. `mins=15`, then picks the hour. This means that the first trigger occurs
at 3:15. Subsequent behaviour will be correct, but the first trigger would be
expected at 3:00. The solution is to delay start until the minutes value is in
the range`45 < mins <= 59`. The general solution is to delay until just before
the first expected callback:

```python
def wait_for(**kwargs):
    tim = mktime(localtime()[:3] + (0, 0, 0, 0, 0))  # Midnight last night
    now = round(time())
    scron = cron(**kwargs)  # Cron instance for search.
    while tim < now:  # Find first event in sequence
        # Defensive. scron should never return 0, but if it did the loop would never quit
        tim += max(scron(tim), 1)
    twait = tim - now - 2  # Wait until 2 secs before first trigger
    if twait > 0:
        sleep(twait)
    while True:
        now = round(time())
        tw = scron(now)
        sleep(tw + 2)
```

##### [Top](./SCHEDULE.md#0-contents)

# 8. The simulate script

In `sched/simulate.py`. This enables the behaviour of sets of args to `schedule`
to be rapidly checked. The `sim` function should be adapted to reflect the
application specifics. The default is:
```python
def sim(*args):
    set_time(*args)
    cs = cron(hrs = 0, mins = 59)
    wait(cs)
    cn = cron(wday=(0, 5), hrs=(1, 10), mins = range(0, 60, 15))
    for _ in range(10):
        wait(cn)
        print("Run payload.\n")

sim(2023, 3, 29, 15, 20, 0)  # Start time: year, month, mday, hrs, mins, secs
```
The `wait` function returns immediately, but prints the length of the delay and
the value of system time when the delay ends. In this instance the start of a
sequence is delayed to ensure that the first trigger occurs at 01:00.

##### [Top](./SCHEDULE.md#0-contents)

# 9. Daylight saving time

Thanks are due to @rhermanklink for raising this issue.

This module is primarily intended for use on a microcontroller, where the time
source is a hardware RTC. This is usually set to local time, and must not change
for daylight saving time (DST); on a microcontroller neither this module nor
`asyncio` will work correctly if system time is changed at runtime. Under an OS,
some kind of thaumaturgy enables `asyncio` to tolerate this behaviour.

Internally the module uses local time (`time.time()` and `time.localtime()`) to
retrieve the current time. Under an OS, in a locale where DST is used, the time
returned by these methods does not increase monotonically but is subject to
sudden changes at a DST boundary.

A `cron` instance accepts "time now" measured in seconds from the epoch, and
returns the time to wait for the first scheduled event. This wait time is
calculated on the basis of a monotonic local time. Assume that the time is
10:00:00 on 1st August, and the first scheduled event is at 10:00:00 on 1st
November. The `cron` instance will return the time to wait. The application task
waits for that period, but local clocks will have changed so that the time reads
9:00:00.

The primary application for this module is on microcontrollers. Further, there
are alternatives such as [Python schedule](https://github.com/dbader/schedule)
which are designed to run under an OS. Fixing this would require a timezone
solution; in many cases the application can correct for DST. Consequently this
behaviour has been deemed to be in the "document, don't fix" category.

The following notes are general observations which may be of interest.

### The epoch

The Python `time.time()` method returns the number of seconds since the epoch.
This is computed relative to the system clock; consecutive calls around a DST
change will yield a sudden change (+3600 secs for a +one hour change).
This value may be converted to a time tuple with `time.gmtime(secs)` or with
`time.localtime(secs)`. If UTC and local time differ, for the same value of
`secs` these will produce UTC-relative and localtime-relative tuples.

Consider `time.mktime()`. This converts a time tuple to a number of seconds
since the epoch. The time difference between a specified time and the epoch is
independent of timezone and DST. The specified time and the epoch are assumed to
be defined in the same (unknown, unspecified) time system. Consequently, if a
delay is defined by the difference between two `mktime()` values, that delay
will be unaffected if a DST change occurs between those two values. This may be
verified with the following script:
```py
from time import mktime, gmtime, localtime
from sys import implementation
cpython = implementation.name == 'cpython'
if cpython:
    from time import struct_time

start = [2024, 9, 5, 11, 49, 2, 3, 249, 1]
sept = round(mktime(struct_time(start))) if cpython else mktime(start)

end = start[:]
end[1] += 2  # Same time + 2months Crosses DST boundary in the UK

november = round(mktime(struct_time(end))) if cpython else mktime(end)
print(november - sept)

if november - sept == 5270400:
    print('PASS')
else:
    print('FAIL')
```
This test passes on the Unix build, under CPython, and on MicroPython on a
microcontroller. It also passes under an OS if the system's local time differs
substantially from UTC.

The `cron` module returns a time difference between a passed time value and one
produced by `mktime()`: accordingly `cron` takes no account of local time or
DST. If local time is changed while waiting for the period specified by `cron`,
at the end of the delay, clocks measuring local time will indicate an incorrect
time.

This is only an issue when running under an OS: if it is considered an error, it
should be addressed in application code.
