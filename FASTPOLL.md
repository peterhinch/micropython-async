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

   2.3 [The conventional approach](./FASTPOLL.md#23-the-conventional-approach)

   2.4 [Background](./FASTPOLL.md#24-background)

 3. [A solution](./FASTPOLL.md#3-a-solution)

   3.1 [Low priority yield](./FASTPOLL.md#31-low-priority-yield)

   3.2 [Low priority callbacks](./FASTPOLL.md#32-low-priority-callbacks)

   3.3 [Event loop constructor](./FASTPOLL.md#33-event-loop-constructor)

 4. [The asyn library](./FASTPOLL.md#4-the-asyn-library)

 5. [Heartbeat](./FASTPOLL.md#5-heartbeat)

# 1. Installation

Replace the file core.py on the target hardware with the one supplied.

## 1.1 Benchmarks

The benchmarks directory contains files demonstrating the performance gains
offered by prioritisation. Documentation is in the code.

 * latency.py Shows the effect on latency with and without low priority usage.
 * timing.py Shows the effect on timing with and without low priority usage.
 * rate.py Shows the frequency with which uasyncio schedules minimal coroutines
 (coros).
 * call_lp.py Demos low priority callbacks.

With the exception of call_lp, benchmarks can be run against the official and
experimental versions of usayncio.

# 2. Rationale

Applications may be required to regularly poll a hardware device or a flag set
by an interrupt service routine (ISR). An overrun may occur if the scheduling
of the polling coro is subject to excessive latency. Further, the accuracy of
millisecond level delays can be compromised by the scheduling of other coros.
This variant provides a means of mitigating this by enabling coros to yield
control in a way which prevents them from competing with coros which are ready
for execution. Coros which have yielded in a low priority fashion will not be
scheduled until all other coros are waiting on a nonzero timeout.

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

Assume a hardware interrupt handler sets the ``isr_has_run`` flag.

Assume we have ten instances of ``foo()`` and one instance of ``handle_isr()``.
When ``handle_isr()`` issues ``yield``, its execution will pause for 40ms while
each instance of ``foo()`` is scheduled and performs one iteration. This may be
unacceptable: it may be necessary to poll the flag at a rate high enough to
avoid overruns.

This version provides a mechanism for reducing this latency by enabling the
``foo()`` instances to yield in a low priority manner. In the case where all
coros other than ``handle_isr()`` are low priority the latency is reduced
to 300us.

The benchmark latency.py demonstrates this. Documentation is in the code. It
can be run against the official and experimental versions.

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
``fast()`` will compete with ``foo()`` instances which are pending.

This results in variable delays up to 55ms (10 threads * 4ms + 15ms). The
experimental version can improve this substantially. The degree of improvement
is dependent on other coros regularly yielding with low priority: if any coro
hogs execution for a substantial period that will inevitably contribute to
latency in a cooperative system.

In the somewhat contrived example of 200 tasks each issuing a low priority
yield every 2ms, a 10ms nominal delay produced times in the range 9.7 to 14.4ms
contrasing to 407.9 to 410.9ms using normal scheduling.

The benchmark timing.py demonstrates this. Documentation is in the code. It can
be run against the official and experimental versions.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 2.3 The conventional approach

The official uasyncio package offers only one solution which is is to redesign
``foo()`` to reduce the delay between yields to the scheduler. This can be
difficult or impossible. Further it is inefficient to reduce the delay much
below 2ms as the scheduler takes 230us to schedule a task.

There are cases where the `foo()`` task is not time-critical. One example is
user interface code where a latency as long as 100ms would usually not be
noticed. A system with ten pushbuttons might have ten coros competing for
execution with time critical coros. Another case is of a coro which is not time
critical is one which performs a lengthy calculation whose results are not
required urgently - a possible example being sensor fusion in a drone. An
extreme case is in some astronomy applications where a delay on a complex
calculation running into many minutes would not be apparent.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 2.4 Background

This has been discussed in detail
[in issue 2989](https://github.com/micropython/micropython/issues/2989).

A further discussion on the subject of using the ioread mechanism to achieve
fast scheduling took place
[in issue 2664](https://github.com/micropython/micropython/issues/2664). The final
comment to this issue suggests that it may never be done for drivers written in
Python.

It seems there is no plan to incorporate a priority mechanism in the official
verion of uasyncio but I believe it confers significant advantages for the
reasons discussed above. Hence this variant.

###### [Jump to Contents](./FASTPOLL.md#contents)

# 3. A solution

# 3.1 Low priority yield

Consider this code fragment running under the experimental version:

```python
import uasyncio as asyncio
async def foo():
    while True:
        # Do something
        yield asyncio.low_priority
```

A coro yielding in this way will only be re-scheduled if there are no "normal"
coros ready for execution. A "normal" coro is one that has yielded by any other
means.

A "normal" coro will be executed regardless of any pending low priority coros.
The latter will only run when all normal coros are waiting on a non-zero delay.
An inevitable implication of having this degree of control is that if a coro
issues

```python
while True:
    await asyncio.sleep(0)
    # Do something which does not yield to the scheduler
```

low priority tasks will never be executed. Normal coros must sometimes wait on
a non-zero delay to enable the low priority ones to be scheduled. This is
analogous to running an infinite loop without yielding.

Low priority coros run in a mutually "fair" round-robin fashion.

###### [Jump to Contents](./FASTPOLL.md#contents)

## 3.2 Low priority callbacks

An additional extension provides for a callback function which runs when all
normal coros are waiting on a delay. The following ``EventLoop`` method is
added:

``call_lp`` Call with low priority. Args: ``callback`` the callback to run,
``*args`` any positional args may follow separated by commas.

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

If code is to run under the official or experimental versions the following may
be used:

```python
import uasyncio as asyncio
low_priority = asyncio.low_priority if 'low_priority' in dir(asyncio) else None
```

with a coro issuing ``yield low_priority`` as required.

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
        await asyncio.sleep_ms(500)
        yield low_priority  # Will hang while a coro loops on a zero delay
```

###### [Jump to Contents](./FASTPOLL.md#contents)
