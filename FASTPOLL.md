# A modified version of uasyncio

This document describes an experimental version of uasyncio. Its purpose is to
provide a simple priority mechanism to facilitate the design of applications
with improved millisecond-level timing accuracy and reduced scheduling latency.

###### [Main README](./README.md)

# Contents

 1. [Installation](./FASTPOLL.md#1-installation)

   1.1 [Benchmarks](./FASTPOLL.md#11-benchmarks)

 2. [Rationale](./FASTPOLL.md#2-rationale)

   2.1 [Latency](./FASTPOLL.md#21-latency)

   2.2 [Timing accuracy](./FASTPOLL.md#22-timing-accuracy)

   2.3 [Polling in uasyncio](./FASTPOLL.md#23-polling-in-usayncio)

   2.4 [Background](./FASTPOLL.md#24-background)

 3. [A solution](./FASTPOLL.md#3-a-solution)

   3.1 [Low priority yield](./FASTPOLL.md#31-low-priority-yield)

   3.2 [Low priority callbacks](./FASTPOLL.md#32-low-priority-callbacks)

   3.3 [Event loop constructor](./FASTPOLL.md#33-event-loop-constructor)

 4. [The asyn library](./FASTPOLL.md#4-the-asyn-library)

 5. [Heartbeat](./FASTPOLL.md#5-heartbeat)

# 1. Installation

After installing uasyncio on the target hardware replace core.py with the one
supplied.

## 1.1 Benchmarks

The benchmarks directory contains files demonstrating the performance gains
offered by prioritisation. Documentation is in the code.

 * latency.py Shows the effect on latency with and without low priority usage.
 * timing.py Shows the effect on timing with and without low priority usage.
 * rate.py Shows the frequency with which uasyncio schedules minimal coroutines
 (coros).
 * call_lp.py Demos low priority callbacks.
 * overdue.py Demo of maximum overdue feature.

With the exception of call_lp, benchmarks can be run against the official and
experimental versions of usayncio.

# 2. Rationale

Applications may be required to regularly poll a hardware device or a flag set
by an interrupt service routine (ISR). An overrun may occur if the scheduling
of the polling coroutine (coro) is subject to excessive latency.

Further, a coro issuing ``await asyncio.sleep_ms(t)`` may block for much longer
than ``t`` depending on the number and design of other coros which are pending
execution.

This variant provides a means of mitigating this by enabling coros to yield
control in a way which prevents them from competing with coros which are ready
for execution. Coros which have yielded in a low priority fashion will not be
scheduled until all "normal" coros are waiting on a nonzero timeout. The
benchmarks show that the improvement can exceed two orders of magnitude.

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

Assume a hardware interrupt handler sets the ``isr_has_run`` flag, and that we
have ten instances of ``foo()`` and one instance of ``handle_isr()``. When
``handle_isr()`` issues ``yield``, its execution will pause for 40ms while each
instance of ``foo()`` is scheduled and performs one iteration. This may be
unacceptable: it may be necessary to poll and respond to the flag at a rate
adequate to avoid overruns.

This version provides a mechanism for reducing this latency by enabling the
``foo()`` instances to yield in a low priority manner. In the case where all
coros other than ``handle_isr()`` are low priority the latency is reduced to
250μs - a figure corresponding to the inherent latency of uasyncio.

The benchmark latency.py demonstrates this. Documentation is in the code; it
can be run against both official and experimental versions.

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

Again assume ten instances of ``foo()`` and one of ``fast()``. When ``fast()``
issues ``await asyncio.sleep_ms(15)`` it will not see a 15ms delay. During the
15ms period ``foo()`` instances will be scheduled. When the delay elapses,
``fast()`` will compete with pending ``foo()`` instances.

This results in variable delays up to 55ms (10 tasks * 4ms + 15ms). The
experimental version can improve this substantially. The degree of improvement
is dependent on other coros regularly yielding with low priority: if any coro
hogs execution for a substantial period that will inevitably contribute to
latency in a cooperative system.

In the somewhat contrived example of 200 tasks each issuing a low priority
yield every 2ms, a 10ms nominal delay produced times in the range 9.8 to 10.8ms
contrasing to 407.9 to 410.9ms using normal scheduling.

The benchmark timing.py demonstrates this. Documentation is in the code. It can
be run against the official and experimental versions.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 2.3 Polling in uasyncio

The asyncio library provides various mechanisms for polling a device or flag.
Aside from a polling loop these include awaitable classes and asynchronous
iterators. It is important to appreciate that these mechanisms have the same
drawback as the polling loop: uasyncio schedules tasks by placing them on a
``utimeq`` queue. This is a queue sorted by time-to-run. Tasks at the top of
the queue (i.e. those ready to run) will be scheduled in "fair" round-robin
fashion. This means that unless a task waits on a nonzero delay it will be
rescheduled only after all other such tasks have been scheduled.

A partial solution is to design the competing ``foo()`` tasks to minimise the
delay between yields to the scheduler. This can be difficult or impossible.
Further it is inefficient to reduce the delay much below 2ms as the scheduler
takes 230μs to schedule a task.

Practical cases exist where the ``foo()`` tasks are not time-critical: in such
cases the performance of time critical tasks may be enhanced by enabling
``foo()`` to submit for rescheduling in a way which does not compete with tasks
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
Python. While a driver written in C is an undoubted solution, it's arguable
that the purpose of MicroPython is to facilitate coding in Python where possible.

It seems there is no plan to incorporate a priority mechanism in the official
verion of uasyncio but I believe it confers significant advantages for the
reasons discussed above. Hence this variant.

###### [Jump to Contents](./FASTPOLL.md#contents)

# 3. A solution

The proposed solution is based on the notion of "after" implying a time delay
which can be expected to be less precise than the asyncio standard calls. It
adds the following functions:

 * ``after(t)``  Awaitable. Low priority version of ``sleep(t)``.
 * ``after_ms(t)``  Awaitable. LP version of ``sleep_ms(t)``.

It adds two event loop methods.

 * ``loop.call_after(t, callback, *args)`` Analogous to ``call_later()``.
 Schedule a callback at low priority.
 * ``loop.max_overdue_ms(t=None)`` Forces tasks or callbacks to be scheduled if
 they become more overdue than the period. If the arg is ``None`` the  period
 is left unchanged. A value of 0 restores default scheduler behaviour. In all
 cases the period value is returned.

# 3.1 Low priority yield

Consider this code fragment running under the experimental version:

```python
import uasyncio as asyncio
async def foo():
    while True:
        # Do something
        await asyncio.after(1.5)  # Wait a minimum of 1.5s
        # code
        await asyncio.after_ms(20)  # Wait a minimum of 20ms
```

These ``await`` statements cause the coro to suspend execution for the minimum
time specified. Low priority coros run in a mutually "fair" round-robin fashion.
By default the coro will only be rescheduled when all "normal" coros are waiting
on a nonzero time delay. A "normal" coro is one that has yielded by any other
means.

This behaviour can be overridden to limit the degree to which they can become
overdue. Consider this code:

```python
import uasyncio as asyncio
async def foo():
    while True:
        # Do something
        await asyncio.after(0)
```

By default a coro yielding in this way will be re-scheduled only when there are
no "normal" coros ready for execution i.e. when all are waiting on a nonzero
delay. The implication of having this degree of control is that if a coro
issues

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
loop = asyncio.get_event_loop()
loop.max_overdue_ms(1000)
```

In this instance tasks which have yielded in a low priority manner will be
rescheduled in the presence of pending "normal" tasks if they become overdue by
more than 1s.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 3.2 Low priority callbacks

An additional extension enables a callback function to be scheduled to run when
all normal coros are waiting on a delay. The following ``EventLoop`` method is
added:

``call_after`` Call with low priority. Positional args:  
 1. ``delay`` Minimum delay in secs before callback runs.
 2. ``callback`` The callback to run.
 3. ``*args`` Optional comma-separated positional args for the callback.

The delay specifies a minimum period before the callback will run and may have
a value of 0. It may be a float. The period may be extended depending on other
high and low priority tasks which are pending execution.

A simple demo of this is ``benchmarks/call_lp.py``. Documentation is in the
code.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 3.3 Event loop constructor

The ``get_event_loop`` method supports two optional integer positional args:
defining the queue sizes for normal and low priority (LP) coros. Note that all
coros are initially put in the normal queue. They temporarily employ the LP
queue when they issue a low priority yield or schedule a LP callback.

The default queue size is 42 for both queues. This is sufficient for many
applications.

Code can determine at runtime whether it is running under the official or
experimental version adapting as appropriate: examples are latency.py and
timing.py in the benchmarks directory.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 4. The asyn library

This now uses the low priority (LP) mechanism if available and where
appropriate. It is employed as follows:

 * ``Lock`` class. Uses normal scheduling on the basis that locks should be
 held for brief periods only.
 * ``Event`` class. An optional boolean constructor arg, defaulting ``False``,
 specifies LP scheduling (if available). A ``True`` value provides for cases
 where response to an event is not time-critical.
 * ``Barrier``, ``Semaphore`` and ``BoundedSemaphore`` classes use LP
 scheduling if available. This is on the basis that typical code may wait on
 these objects for some time.

A coro waiting on a ``Lock`` or an ``Event`` which uses normal scheduling will
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
