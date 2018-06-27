# An experimental modified version of uasyncio

This document describes a "priority" version of uasyncio. Its purpose is to
provide a simple priority mechanism to facilitate the design of applications
with improved millisecond-level timing accuracy and reduced scheduling latency.

I am hopeful that uasyncio will support fast I/O polling and have a
[PR](https://github.com/micropython/micropython-lib/pull/287) in place to
implement this. If this (or other solution) is implemented I will deprecate
this module as the I/O mechanism is inherently more efficient with polling
implemented in C.

V0.3 Feb 2018. A single module designed to work with the official `uasyncio`
library. This requires `uasyncio` V2.0 which requires firmware dated
22nd Feb 2018 or later.

**API CHANGES**
V2.0 of `uasyncio` changed the arguments to `get_event_loop` so this version
has corresponding changes. See [section 3](./FASTPOLL.md#3-a-solution).

###### [Main README](./README.md)

# Contents

 1. [Installation](./FASTPOLL.md#1-installation)

  1.1 [Benchmarks](./FASTPOLL.md#11-benchmarks) Benchmark and demo programs.

 2. [Rationale](./FASTPOLL.md#2-rationale)

  2.1 [Latency](./FASTPOLL.md#21-latency)

  2.2 [Timing accuracy](./FASTPOLL.md#22-timing-accuracy)

  2.3 [Polling in uasyncio](./FASTPOLL.md#23-polling-in-usayncio)

  2.4 [Background](./FASTPOLL.md#24-background)

 3. [A solution](./FASTPOLL.md#3-a-solution)

  3.1 [Low priority yield](./FASTPOLL.md#31-low-priority-yield)

   3.1.1 [Task Cancellation and Timeouts](./FASTPOLL.md#311-task-cancellation-and-timeouts)

  3.2 [Low priority callbacks](./FASTPOLL.md#32-low-priority-callbacks)

  3.3 [High priority tasks](./FASTPOLL.md#33-high-priority-tasks)

 4. [The asyn library](./FASTPOLL.md#4-the-asyn-library)

 5. [Heartbeat](./FASTPOLL.md#5-heartbeat)

 6. [ESP Platforms](./FASTPOLL.md#6-esp-platforms)

# 1. Installation

Install and test uasyncio on the target hardware. Copy `asyncio_priority.py`
to the target. Users of previous versions should update any of the benchmark
programs which are to be run.

In MicroPython 1.9 `uasyncio` was implemented as a frozen module on the
ESP8266. This version is not compatible with `asyncio_priority.py`. Given the
limited resources of the ESP8266 `uasyncio` and `uasyncio_priority` should be
implemented as frozen bytecode. See
[ESP Platforms](./FASTPOLL.md#6-esp-platforms) for general comments on the
suitability of ESP platforms for systems requiring fast response.

## 1.1 Benchmarks

The benchmarks directory contains files demonstrating the performance gains
offered by prioritisation. They also offer illustrations of the use of these
features. Documentation is in the code.

 * `benchmarks/latency.py` Shows the effect on latency with and without low
 priority usage.
 * `benchmarks/timing.py` Shows the effect on timing with and without low
 priority usage.
 * ``benchmarks/rate.py` Shows the frequency with which the official uasyncio
 schedules minimal coroutines (coros).
 * `benchmarks/rate_p.py` As above, but measures the overhead of the priority
 extension.
 * `benchmarks/call_lp.py` Demos low priority callbacks.
 * `benchmarks/overdue.py` Demo of maximum overdue feature.
 * `benchmarks/priority.py` Demo of high priority coro.
 * `priority_test.py` Cancellation of low priority coros.

With the exceptions of call_lp and priority.py, benchmarks can be run against
the official and priority versions of usayncio.

# 2. Rationale

Applications may need to poll a hardware device or a flag set by an interrupt
service routine (ISR). An overrun may occur if the scheduling of the polling
coroutine (coro) is subject to excessive latency.

Further, a coro issuing `await asyncio.sleep_ms(t)` may block for much longer
than `t` depending on the number and design of other coros which are pending
execution.

This variant mitigates this by enabling coros to yield control in a way which
prevents them from competing with coros which are ready for execution. Coros
which have yielded in a low priority fashion will not be scheduled until all
"normal" coros are waiting on a nonzero timeout. The benchmarks show that the
improvement can exceed two orders of magnitude.

It also provides for fast scheduling where a user supplied callback is tested
on every iteration of the scheduler. This minimises latency at some cost to
overall performance.

## 2.1 Latency

Coroutines in uasyncio which are pending execution are scheduled in a "fair"
round-robin fashion. Consider these functions:

```python
async def foo():
    while True:
        yield
        # code which takes 4ms to complete

async def handle_isr():
    global isr_has_run
    while True:
        if isr_has_run:
            # read and process data
            isr_has_run = False
        yield
```

Assume a hardware interrupt handler sets the `isr_has_run` flag, and that we
have ten instances of `foo()` and one instance of `handle_isr()`. When
`handle_isr()` issues `yield`, its execution will pause for 40ms while each
instance of `foo()` is scheduled and performs one iteration. This may be
unacceptable: it may be necessary to poll and respond to the flag at a rate
adequate to avoid overruns.

This version provides a mechanism for reducing this latency by enabling the
`foo()` instances to yield in a low priority manner. In the case where all
coros other than `handle_isr()` are low priority the latency is reduced to
250μs - a figure close to the inherent latency of uasyncio.

The benchmark latency.py demonstrates this. Documentation is in the code; it
can be run against both official and priority versions. This measures scheduler
latency. Maximum application latency, measured relative to the incidence of an
asynchronous event, will be 250μs plus the worst-case delay between yields of
any one competing task.

Where a coro must respond rapidly to an event, the scheduler can test a user
supplied callback on every iteration. See
[section 3.3](./FASTPOLL.md#33-high-priority-tasks).

###### [Jump to Contents](./FASTPOLL.md#contents)

## 2.2 Timing accuracy

Consider these functions:

```python
async def foo():
    while True:
        await asyncio.sleep(0)
        # code which takes 4ms to complete

async def fast():
    while True:
        # Code omitted
        await asyncio.sleep_ms(15)
        # Code omitted
```

Again assume ten instances of `foo()` and one of `fast()`. When `fast()`
issues `await asyncio.sleep_ms(15)` it will not see a 15ms delay. During the
15ms period `foo()` instances will be scheduled. When the delay elapses,
`fast()` will compete with pending `foo()` instances.

This results in variable delays up to 55ms (10 tasks * 4ms + 15ms). The
priority version can improve this substantially. The degree of improvement
is dependent on other coros regularly yielding with low priority: if any coro
hogs execution for a substantial period that will inevitably contribute to
latency in a cooperative system.

In the somewhat contrived example of 200 tasks each issuing a low priority
yield every 2ms, a 10ms nominal delay produced times in the range 9.8 to 10.8ms
contrasing to 407.9 to 410.9ms using normal scheduling.

The benchmark timing.py demonstrates this. Documentation is in the code. It can
be run against the official and priority versions.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 2.3 Polling in uasyncio

The asyncio library provides various mechanisms for polling a device or flag.
Aside from a polling loop these include awaitable classes and asynchronous
iterators. It is important to appreciate that these mechanisms have the same
drawback as the polling loop: uasyncio schedules tasks by placing them on a
`utimeq` queue. This is a queue sorted by time-to-run. Tasks which are ready
to run are scheduled in "fair" round-robin fashion. This means that a task
waiting on a zero delay will be rescheduled only after the scheduling of all
other such tasks (including timed waits whose time has elapsed).

A partial solution is to design the competing `foo()` tasks to minimise the
delay between yields to the scheduler. This can be difficult or impossible.
Further it is inefficient to reduce the delay much below 2ms as the scheduler
takes ~200μs to schedule a task.

Practical cases exist where the `foo()` tasks are not time-critical: in such
cases the performance of time critical tasks may be enhanced by enabling
`foo()` to submit for rescheduling in a way which does not compete with tasks
requiring a fast response. In essence "slow" operations tolerate longer latency
and longer time delays so that fast operations meet their performance targets.
Examples are:

 * User interface code. A system with ten pushbuttons might have a coro running
 on each. A GUI touch detector coro needs to check a touch against sequence of
 objects. Both may tolerate 100ms of latency before users notice any lag.
 * Networking code: a latency of 100ms may be dwarfed by that of the network.
 * Mathematical code: there are cases where time consuming calculations may
 take place which are tolerant of delays. Examples are statistical analysis,
 sensor fusion and astronomical calculations.
 * Data logging.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 2.4 Background

This has been discussed in detail
[in issue 2989](https://github.com/micropython/micropython/issues/2989).

A further discussion on the subject of using the ioread mechanism to achieve
fast scheduling took place
[in issue 2664](https://github.com/micropython/micropython/issues/2664). The final
comment to this issue suggests that it may never be done for drivers written in
Python. While a driver written in C is an undoubted solution, the purpose of
MicroPython is arguably to facilitate coding in Python where possible.

It seems there is no plan to incorporate a priority mechanism in the official
verion of uasyncio but I believe it confers significant advantages for the
reasons discussed above. Hence this variant.

###### [Jump to Contents](./FASTPOLL.md#contents)

# 3. A solution

The module enables coroutines to yield to the scheduler with three levels of
priority, one with higher and one with lower priority than standard. It
provides a replacement for `uasyncio.get_event_loop()` enabling the queue
sizes to be set.

`aysncio_priority.get_event_loop(runq_len, waitq_len, lpqlen)`  
Arguments:  
 1. `runq_len` Length of normal queue. Default 16 tasks.
 2. `waitq_len` Length of wait queue. Default 16.
 3. `lpqlen` Length of low priority queue. Default 16.

The low priority solution is based on the notion of "after" implying a time
delay which can be expected to be less precise than the asyncio standard calls.
The optional high priority mechanism adds "when" implying scheduling when a
condition is met. The library adds the following awaitable instances:

 * `after(t)`  Low priority version of `sleep(t)`.
 * `after_ms(t)`  LP version of `sleep_ms(t)`.
 * `when(callback)` Re-schedules when the callback returns True.

It adds the following event loop methods:

 * `loop.call_after(t, callback, *args)`
 * `loop.call_after_ms(t, callback, *args)`
 * `loop.max_overdue_ms(t=None)` This sets the maximum time a low priority task
 will wait before being  scheduled. A value of 0 corresponds to no limit. The
 default arg `None` leaves the period unchanged. Always returns the period
 value.

See [Low priority callbacks](./FASTPOLL.md#32-low-priority-callbacks)

## 3.1 Low priority yield

Consider this code fragment:

```python
import asyncio_priority as asyncio
loop = asyncio.get_event_loop()

async def foo():
    while True:
        # Do something
        await asyncio.after(1.5)  # Wait a minimum of 1.5s
        # code
        await asyncio.after_ms(20)  # Wait a minimum of 20ms
```

These `await` statements cause the coro to suspend execution for the minimum
time specified. Low priority coros run in a mutually "fair" round-robin fashion.
By default the coro will only be rescheduled when all "normal" coros are waiting
on a nonzero time delay. A "normal" coro is one that has yielded by any other
means.

This behaviour can be overridden to limit the degree to which they can become
overdue. For the reasoning behind this consider this code:

```python
import asyncio_priority as asyncio

async def foo():
    while True:
        # Do something
        await asyncio.after(0)
```

By default a coro yielding in this way will be re-scheduled only when there are
no "normal" coros ready for execution i.e. when all are waiting on a nonzero
delay. The implication of having this degree of control is that if a coro
issues:

```python
while True:
    await asyncio.sleep(0)
    # Do something which does not yield to the scheduler
```

low priority tasks will never be executed. Normal coros must sometimes wait on
a non-zero delay to enable the low priority ones to be scheduled. This is
analogous to running an infinite loop without yielding.

This behaviour can be modified by issuing:

```python
loop = asyncio.get_event_loop(max_overdue_ms = 1000)
```

In this instance a task which has yielded in a low priority manner will be
rescheduled in the presence of pending "normal" tasks if they become overdue by
more than 1s.

### 3.1.1 Task Cancellation and Timeouts

Tasks which yield in a low priority manner may be subject to timeouts or be
cancelled in the same way as normal tasks. See [Task cancellation](./TUTORIAL.md#36-task-cancellation)
and [Coroutines with timeouts](./TUTORIAL.md#44-coroutines-with-timeouts).

###### [Jump to Contents](./FASTPOLL.md#contents)

## 3.2 Low priority callbacks

The following `EventLoop` methods enable callback functions to be scheduled
to run when all normal coros are waiting on a delay or when `max_overdue_ms`
has elapsed:

`call_after` Schedule a callback with low priority. Positional args:  
 1. `delay`  Minimum delay in seconds. May be a float or integer.
 2. `callback` The callback to run.
 3. `*args` Optional comma-separated positional args for the callback.

The delay specifies a minimum period before the callback will run and may have
a value of 0. The period may be extended depending on other high and low
priority tasks which are pending execution.

A simple demo of this is `benchmarks/call_lp.py`. Documentation is in the
code.

`call_after_ms(delay, callback, *args)` Call with low priority. Positional
args:  
 1. `delay` Integer. Minimum delay in millisecs before callback runs.
 2. `callback` The callback to run.
 3. `*args` Optional positional args for the callback.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 3.3 High priority tasks

Where latency must be reduced to the absolute minimum, a condition may be
tested on every iteration of the scheduler. This involves yielding a callback
function which returns a boolean. When a coro yields to the scheduler, each
pending callback is run until one returns `True` when that task is run. If
there are no pending callbacks which return `True` it will schedule other
tasks.

This machanism should be used only if the application demands it. Caution is
required since running the callbacks inevitably impacts the performance of
the scheduler. To minimise this callbacks should be short (typically returning
a boolean flag set by a hard interrupt handler) and the number of high priority
tasks should be small.

The benchmark priority.py demonstrates and tests this mechanism.

To yield at high priority issue

```python
import asyncio_priority as asyncio

async def foo():
    while True:
        await asyncio.when(callback)  # Pauses until callback returns True
        # Code omitted - typically queue received data for processing
        # by another coro
```

Pending callbacks are stored in a list which grows dynamically. An application
will typically have only one or two coroutines which wait on callbacks so the
list will never grow beyond this length.

In the current implementation the callback takes no arguments. However it can
be a bound method, enabling it to access class and instance variables.

No means of scheduling a high priority callback analogous to `call_soon` is
provided. If such a mechanism existed, the cb would run immediately the coro
yielded, with the coro being rescheduled once the cb returned `True`. This
behaviour can be achieved more efficiently by simply calling the function.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 4. The asyn library

This now uses the low priority (LP) mechanism if available and where
appropriate. It is employed as follows:

 * `Lock` class. Uses normal scheduling on the basis that locks should be
 held for brief periods only.
 * `Event` class. An optional boolean constructor arg, defaulting `False`,
 specifies LP scheduling (if available). A `True` value provides for cases
 where response to an event is not time-critical.
 * `Barrier`, `Semaphore` and `BoundedSemaphore` classes use LP
 scheduling if available. This is on the basis that typical code may wait on
 these objects for some time.

A coro waiting on a `Lock` or an `Event` which uses normal scheduling will
therefore prevent the execution of LP tasks for the duration.

###### [Jump to Contents](./FASTPOLL.md#contents)

# 5. Heartbeat

I find it useful to run a "heartbeat" coro in development as a simple check
for code which has failed to yield. If the low priority mechanism is used this
can be extended to check that no coro loops indefinitely on a zero delay.

```python
async def heartbeat(led):
    while True:
        led.toggle()
        await after_ms(500)  # Will hang while a coro loops on a zero delay
```

###### [Jump to Contents](./FASTPOLL.md#contents)

# 6. ESP Platforms

It should be noted that the response of the ESP8266 to hardware interrupts is
remarkably slow. This also appears to apply to ESP32 platforms. Consider
whether a response in the high hundreds of μs meets project requirements; also
whether a priority mechanism is needed on hardware with such poor realtime
performance.
