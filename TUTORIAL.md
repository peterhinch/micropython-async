# Application of uasyncio to hardware interfaces

This document is a "work in progress" as I learn the content myself. Further
at the time of writing uasyncio is itself under development. It is likely that
these notes may contain errors; please report any you discover.

The MicroPython uasyncio library comprises a subset of Python's asyncio library
designed for use on microcontrollers. As such it has a small RAM footprint and
fast context switching with zero RAM allocation. This document describes its
use with a focus on interfacing hardware devices. The aim is to design drivers
in such a way that the application continues to run while the driver is waiting
for a response from the hardware or for a user interaction.

Another major application area for asyncio is in network programming: many
guides to this may be found online.

###### [Main README](./README.md)

# Contents

 1. [Cooperative scheduling](./TUTORIAL.md#1-cooperative-scheduling)
  
   1.1 [Modules](./TUTORIAL.md#11-modules)

 2. [uasyncio](./TUTORIAL.md#2-uasyncio)

  2.1 [Program structure: the event loop](./TUTORIAL.md#21-program-structure-the-event-loop)
  
  2.2 [Coroutines (coros)](./TUTORIAL.md#22-coroutines-coros)

   2.2.1 [Queueing a coro for scheduling](./TUTORIAL.md#221-queueing-a-coro-for-scheduling)

   2.2.2 [Running a callback function](./TUTORIAL.md#222-running-a-callback-function)

   2.2.3 [Notes](./TUTORIAL.md#223-notes) Coros as bound methods. Returning values.

  2.3 [Delays](./TUTORIAL.md#23-delays)

 3. [Synchronisation](./TUTORIAL.md#3-synchronisation)

  3.1 [Lock](./TUTORIAL.md#31-lock)

  3.2 [Event](./TUTORIAL.md#32-event)

   3.2.1 [The event's value](./TUTORIAL.md#321-the-events-value)

  3.3 [Barrier](./TUTORIAL.md#33-barrier)

  3.4 [Semaphore](./TUTORIAL.md#34-semaphore)

   3.4.1 [BoundedSemaphore](./TUTORIAL.md#341-boundedsemaphore)

  3.5 [Queue](./TUTORIAL.md#35-queue)

  3.6 [Task cancellation](./TUTORIAL.md#36-task-cancellation)

 4. [Designing classes for asyncio](./TUTORIAL.md#4-designing-classes-for-asyncio)

  4.1 [Awaitable classes](./TUTORIAL.md#41-awaitable-classes)

  4.2 [Asynchronous iterators](./TUTORIAL.md#42-asynchronous-iterators)

  4.3 [Asynchronous context managers](./TUTORIAL.md#43-asynchronous-context-managers)
  
  4.4 [Coroutines with timeouts](./TUTORIAL.md#44-coroutines-with-timeouts)

 5. [Device driver examples](./TUTORIAL.md#5-device-driver-examples)

  5.1 [The IORead mechnaism](./TUTORIAL.md#51-the-ioread-mechanism)

  5.2 [Using a coro to poll hardware](./TUTORIAL.md#52-using-a-coro-to-poll-hardware)

  5.3 [Using IORead to poll hardware](./TUTORIAL.md#53-using-ioread-to-poll-hardware)

  5.4 [A complete example: aremote.py](./TUTORIAL.md#54-a-complete-example-aremotepy)

 6. [Hints and tips](./TUTORIAL.md#6-hints-and-tips)

  6.1 [Program hangs](./TUTORIAL.md#61-program-hangs)

  6.2 [uasyncio retains state](./TUTORIAL.md#62-uasyncio-retains-state)

  6.3 [Garbage Collection](./TUTORIAL.md#63-garbage-collection)

  6.4 [Testing](./TUTORIAL.md#64-testing)

 7. [Notes for beginners](./TUTORIAL.md#7-notes-for-beginners)

  7.1 [Why Scheduling?](./TUTORIAL.md#71-why-scheduling)

  7.2 [Why cooperative rather than pre-emptive?](./TUTORIAL.md#72-why-cooperative-rather-than-pre-emptive)

  7.3 [Communication](./TUTORIAL.md#73-communication)

  7.4 [Polling](./TUTORIAL.md#74-polling)

 8. [Modifying uasyncio](./TUTORIAL.md#8-modifying-uasyncio)

# 1. Cooperative scheduling

The technique of cooperative multi-tasking is widely used in embedded systems.
It offers lower overheads than pre-emptive scheduling and avoids many of the
pitfalls associated with truly asynchronous threads of execution. For those new
to asynchronous programming there is an introduction
[here](./TUTORIAL.md#7-notes-for-beginners).

###### [Jump to Contents](./TUTORIAL.md#contents)

## 1.1 Modules

The following modules and test programs are provided. The first two are the
most immediately rewarding as they produce visible results by accessing Pyboard
hardware.

 1. ``aledflash.py`` Flashes the four Pyboard LED's asynchronously for 10s. The
 simplest uasyncio demo. Import it to run.
 2. ``apoll.py`` A device driver for the Pyboard accelerometer. Demonstrates
 the use of a coroutine to poll a device. Runs for 20s. Import it to run.
 3. ``aswitch.py`` This provides classes for interfacing switches and
 pushbuttons and also a software retriggerable delay object. Pushbuttons are a
 generalisation of switches providing logical rather than physical status along
 with double-clicked and long pressed events.
 4. ``astests.py`` Test/demonstration programs for the above.
 5. ``asyn.py`` Synchronisation primitives ``Lock``, ``Event``, ``Barrier``,
 ``Semaphore``, ``BoundedSemaphore`` and ``Cancellable``.
 6. ``asyntest.py`` Example/demo programs for above.
 7. ``roundrobin.py`` Demo of round-robin scheduling. Also a benchmark of
 scheduling performance.
 8. ``awaitable.py`` Demo of an awaitable class. One way of implementing a
 device driver which polls an interface.
 9. ``chain.py`` Copied from the Python docs. Demo of chaining coroutines.
 10. ``aqtest.py`` Demo of uasyncio ``Queue`` class.
 11. ``aremote.py`` Example device driver for NEC protocol IR remote control.
 12. ``auart.py`` Demo of streaming I/O via a Pyboard UART.
 13. ``asyncio_priority.py`` An version of uasyncio with a simple priority
 mechanism. See [this doc](./FASTPOLL.md).

The ``benchmarks`` directory contains scripts to test and characterise the
uasyncio scheduler. See [this doc](./FASTPOLL.md).

###### [Jump to Contents](./TUTORIAL.md#contents)

# 2. uasyncio

The asyncio concept is of cooperative multi-tasking based on coroutines,
referred in this document as coros.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 2.1 Program structure: the event loop

Consider the following example:

```python
import uasyncio as asyncio
loop = asyncio.get_event_loop()
async def bar():
    count = 0
    while True:
        count += 1
        print(count)
        await asyncio.sleep(1)  # Pause 1s

loop.create_task(bar()) # Schedule ASAP
loop.run_forever()
```

Program execution proceeds normally until the call to ``loop.run_forever``. At
this point execution is controlled by the scheduler. A line after
``loop.run_forever`` would never be executed. The scheduler runs ``bar``
because this has been placed on the scheduler's queue by ``loop.create_task``.
In this trivial example there is only one coro: ``bar``. If there were others,
the scheduler would schedule them in periods when ``bar`` was paused.

Many embedded applications have an event loop which runs continuously. The event
loop can also be started in a way which permits termination, by using the event
loop's ``run_until_complete`` method. Examples of this may be found in the
``astests.py`` module.

The event loop instance is a singleton, instantiated by a program's first call
to ``asyncio.get_event_loop()``. This takes an optional integer arg being the
length of the coro queue - i.e. the maximum number of concurrent coros allowed.
The default of 42 is likely to be adequate for most purposes. If a coro needs
to call an event loop method, calling ``asyncio.get_event_loop()`` (without
args) will efficiently return it.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 2.2 Coroutines (coros)

A coro is instantiated as follows:

```python
async def foo(delay_secs):
    await asyncio.sleep(delay_secs)
    print('Hello')
```

A coro can allow other coroutines to run by means of the ``await coro``
statement. A coro must contain at least one ``await`` statement. This causes
``coro`` to run to completion before execution passes to the next instruction.
Consider these lines of code:

```python
await asyncio.sleep(delay_secs)
await asyncio.sleep(0)
```

The first causes the code to pause for the duration of the delay, with other
coros being scheduled for the duration. A delay of 0 causes any pending coros
to be scheduled in round-robin fashion before the following line is run. See
the ``roundrobin.py`` example.

###### [Jump to Contents](./TUTORIAL.md#contents)

### 2.2.1 Queueing a coro for scheduling

 * ``EventLoop.create_task`` Arg: the coro to run. The scheduler queues the
 coro to run ASAP. The ``create_task`` call returns immediately. The coro
 arg is specified with function call syntax with any required arguments passed.
 * ``EventLoop.run_until_complete`` Arg: the coro to run. The scheduler queues
 the coro to run ASAP. The coro arg is specified with function call syntax with
 any required arguments passed. The ``run_until_complete`` call returns when
 the coro terminates: this method provides a way of quitting the scheduler.
 * ``await``  Arg: the coro to run, specified with function call syntax. Starts
 the coro ASAP and blocks until it has run to completion.

The above are compatible with CPython. Additional uasyncio methods are
discussed in 2.2.3 below.

###### [Jump to Contents](./TUTORIAL.md#contents)

### 2.2.2 Running a callback function

Callbacks should be Python functions designed to complete in a short period of
time as coroutines will have no opportunity to run for the duration.

The following ``EventLoop`` methods schedule callbacks:

 1. ``call_soon`` Call as soon as possible. Args: ``callback`` the callback to
 run, ``*args`` any positional args may follow separated by commas.
 2. ``call_later`` Call after a delay in secs. Args: ``delay``, ``callback``,
 ``*args``
 3. ``call_later_ms`` Call after a delay in ms. Args: ``delay``, ``callback``,
 ``args``. Args are stored in a tuple for efficiency. Default an empty
 tuple ``()``.

```python
loop = asyncio.get_event_loop()
loop.call_soon(foo, 5) # Schedule callback 'foo' ASAP with an arg of 5
loop.call_later(2, foo, 5) # Schedule after 2 seconds
loop.call_later_ms(50, foo, (5,)) # Schedule after 50ms. Note arg in tuple.
loop.run_forever()
```

###### [Jump to Contents](./TUTORIAL.md#contents)

### 2.2.3 Notes

A coro can contain a ``return`` statement with arbitrary return values. To
retrieve them issue:

```python
result = await my_coro()
```

Coros may be bound methods.

For CPython compatibility a coro must contain at least one ``await`` statement.
Using ``yield`` in a coro provokes a syntax error in CPython. However uasyncio
allows it as an alternative to ``await``. The following are uasyncio
extensions (in addition to those introduced above in section 2.2.2):

```python
yield from coro  # Equivalent to await coro: continue when coro terminates
yield  # Reschedule current coro in round-robin fashion
yield None  # As above
await asyncio.sleep_ms(100)  # Pause for 100ms and schedule other coros.
yield 100  # Pause 100ms - equivalent to above
```

The ``yield`` syntax should be regarded as povisional: it is possible that its
support may be removed in future uasyncio versions.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 2.3 Delays

Where a delay is required in a coro there are two options. For longer delays and
those where the duration need not be precise, the following should be used:

```python
async def foo(delay_secs, delay_ms):
    await asyncio.sleep(delay_secs)
    print('Hello')
    await asyncio.sleep_ms(delay_ms)
```

While these delays are in progress the scheduler will schedule other coros.
This is generally highly desirable, but it does introduce uncertainty in the
timing as the calling routine will only be rescheduled when the one running at
the appropriate time has yielded. The amount of latency depends on the design
of the application, but is likely to be on the order of tens or hundreds of ms;
this is discussed further in [Section 5](./TUTORIAL.md#5-device-driver-examples).

Very precise delays may be issued by using the ``utime`` functions ``sleep_ms``
and ``sleep_us``. These are best suited for short delays as the scheduler will
be unable to schedule other coros while the delay is in progress.

###### [Jump to Contents](./TUTORIAL.md#contents)

# 3 Synchronisation

There is often a need to provide synchronisation between coros. A common
example is to avoid what are known as "race conditions" where multiple coros
compete to access a single resource. An example is provided in the ``astests.py``
program and discussed in [the docs](./DRIVERS.md). Another hazard is the "deadly
embrace" where two coros wait on the other's completion.

In simple applications these are often addressed with global flags. A more
elegant approach is to use synchronisation primitives. The module ``asyn.py``
offers "micro" implementations of ``Lock``, ``Event``, ``Barrier`` and ``Semaphore``
primitives. These are for use only with asyncio. They are not thread safe and
should not be used with the ``_thread`` module.

Another synchronisation issue arises with producer and consumer coros. The
producer generates data which the consumer uses. Asyncio provides the ``Queue``
object. The producer puts data onto the queue while the consumer waits for its
arrival (with other coros getting scheduled for the duration). The ``Queue``
guarantees that items are removed in the order in which they were received.
Alternatively a ``Barrier`` instance can be used if the producer must wait
until the consumer is ready to access the data.

The interface specification for the primitives is [here](./PRIMITIVES.md).

###### [Jump to Contents](./TUTORIAL.md#contents)

## 3.1 Lock

This guarantees unique access to a shared resource. The preferred way to use it
is via an asynchronous context manager. In the following code sample a ``Lock``
instance ``lock`` has been created and is passed to all coros wishing to access
the shared resource. Each coro issues the following:

```python
async def bar(lock):
    async with lock:
        # Access resource
```

While the coro ``bar`` is accessing the resource, other coros will pause at the
``async with lock`` statement until the context manager in ``bar()`` is
complete.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 3.2 Event

This provides a way for one or more coros to pause until another flags them to
continue. An ``Event`` object is instantiated and made accessible to all coros
using it. Coros waiting on the event issue ``await event`` whereupon execution
pauses until another issues ``event.set()``.

This presents a problem if ``event.set()`` is issued in a looping construct; the
code must wait until the event has been accessed by all waiting coros before
setting it again. In the case where a single coro is awaiting the event this
can be achieved by the receiving coro clearing the event:

```python
async def eventwait(event):
    await event
    event.clear()
```

The coro raising the event checks that it has been serviced:

```python
async def foo(event):
    while True:
        # Acquire data from somewhere
        while event.is_set():
            await asyncio.sleep(1) # Wait for coro to respond
        event.set()
```

Where multiple coros wait on a single event synchronisationcan be achieved by
means of an acknowledge event. Each coro needs a separate event.

```python
async def eventwait(event, ack_event):
    await event
    ack_event.set()
```

An example of this is provided in the ``event_test`` function in ``asyntest.py``.
This is cumbersome. In most cases - even those with a single waiting coro - the
Barrier class below offers a simpler approach.

An Event can also provide a means of communication between an interrupt handler
and a coro. The handler services the hardware and sets an event which is tested
in slow time by the coro.

###### [Jump to Contents](./TUTORIAL.md#contents)

### 3.2.1 The event's value

The ``event.set()`` method can accept an optional data value of any type. A
coro waiting on the event can retrieve it by means of ``event.value()``. Note
that ``event.clear()`` will set the value to ``None``. A typical use for this
is for the coro setting the event to issue ``event.set(loop.time())``. Any coro
waiting on the event can determine the latency incurred, for example to perform
compensation for this.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 3.3 Barrier

This enables multiple coros to rendezvous at a particular point. For example
producer and consumer coros can synchronise at a point where the producer has
data available and the consumer is ready to use it. At that point in time the
``Barrier`` can optionally run a callback before releasing the barrier and
allowing all waiting coros to continue.

The callback can be a function or a coro. In most applications a function is
likely to be used: this can be guaranteed to run to completion before the
barrier is released.

An example is the ``barrier_test`` function in ``asyntest.py``. In the code
fragment from that program:

```python
def callback(text):
    print(text)

barrier = Barrier(3, callback, ('Synch',))

async def report():
    for i in range(5):
        print('{} '.format(i), end='')
        await barrier
```

multiple instances of ``report`` print their result and pause until the other
instances are also complete. At that point the callback runs. On its completion
the coros resume.

A special case of `Barrier` usage is where some coros are allowed to pass the
barrier, registering the fact that they have done so. At least one coro must
wait on the barrier. It will continue execution when all non-waiting coros have
passed the barrier, and all other waiting coros have reached it. This can be of
use when cancelling coros. A coro which cancels others might wait until all
cancelled coros have passed the barrier as they quit.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 3.4 Semaphore

A semaphore limits the number of coros which can access a resource. It can be
used to limit the number of instances of a particular coro which can run
concurrently. It performs this using an access counter which is initialised by
the constructor and decremented each time a coro acquires the semaphore.

The easiest way to use it is with a context manager:

```python
async def foo(sema):
    async with sema:
        # Limited access here
```
An example is the ``semaphore_test`` function in ``asyntest.py``.

###### [Jump to Contents](./TUTORIAL.md#contents)

### 3.4.1 BoundedSemaphore

This works identically to the ``Semaphore`` class except that if the ``release``
method causes the access counter to exceed its initial value, a ``ValueError``
is raised.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 3.5 Queue

The sample program ``aqtest.py`` demonstrates simple use of this class. A
typical producer coro might work as follows:

```python
async def producer(q):
    while True:
        result = await slow_process()  # somehow get some data
        await q.put(result)  # may pause if a size limited queue fills
```

and the consumer works along these lines:

```python
async def consumer(q):
    while True:
        result = await(q.get())  # Will pause if q is empty
        print('Result was {}'.format(result))
```

The ``Queue`` class provides significant additional functionality in that the
size of queues may be limited and the status may be interrogated. The behaviour
on empty status and (where size is limited) the behaviour on full status may be
controlled. Documentation of this is in the code.

An example of its use is provided in ``aqtest.py``.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 3.6 Task cancellation

At the time of writing (12th Nov 2017) this requires PR #3380 and
micropython-lib PR #221 which are yet to be merged.

The `uasyncio` library supports task cancellation by throwing an exception to
the coro which is to be cancelled. The latter must trap the exception and
(after performing any cleanup) terminate. The use of this mechanism is
facilitated by the `Cancellable` class which enables a coro to be associated
with a user-defined name for cancellation. Examples of its usage may be found
in `asyntest.py`.

A cancellable coro is instantiated from a normal coro `foo()` by means of
`Cancellable(foo(5), 'foo')`. Note the passing of an argument to the coro. A
coro can `await` such a task with `await Cancellable(foo(5), 'foo')`.
Alternatively a cancellable task may be scheduled for execution with
`loop.create_task(Cancellable(foo(5), 'foo').task)`.

In either case the coro with the user-defined name 'foo' may be cancelled with
`Cancellable.cancel('foo')`. The coro `foo` will receive the `CancelError` when
it next runs. This means that in real time, and from the point of view of the
coro which has cancelled it, cancellation may not be immediate. In some
situations this may matter. Synchronisation may be achieved using the `Barrier`
class, with the cancelling task pausing until all the coros it has cancelled
have processed the exception. The following - adapted from `asyntest.py` - 
illustrates this.

```python
import uasyncio as asyncio
from asyn import Barrier, Cancellable, CancelError

async def forever(n):
    print('Started forever() instance', n)
    while True:  # Run until cancelled. Error propagates to caller.
        await asyncio.sleep(7 + n)
        print('Running instance', n)

barrier = Barrier(3)  # 3 tasks share the barrier

async def rats(n):
    # Cancellable coros must trap the CancelError
    try:
        await forever(n)  # Error propagates up from forever()
    except CancelError:
        await barrier(nowait = True)  # Quit immediately
        print('Instance', n, 'was cancelled')

async def run_cancel_test2():
    loop = asyncio.get_event_loop()
    loop.create_task(Cancellable(rats(1), 'rats_1').task)
    loop.create_task(Cancellable(rats(2), 'rats_2').task)
    print('Running two tasks')
    await asyncio.sleep(10)
    print('About to cancel tasks')
    Cancellable.cancel('rats_1')
    Cancellable.cancel('rats_2')
    await barrier  # Continue when dependent tasks have quit
    print('tasks were cancelled')

loop = asyncio.get_event_loop()
loop.run_until_complete(run_cancel_test2())
```

In the line `await barrier(nowait = True)` the `nowait` argument is for
efficiency. It is not required by the program logic. Its purpose is to remove
the redundant task from the task queue as soon as possible so that it ceases to
use processor time.

###### [Jump to Contents](./TUTORIAL.md#contents)

# 4 Designing classes for asyncio

In the context of device drivers the aim is to ensure nonblocking operation.
The design should ensure that other coros get scheduled in periods while the
driver is waiting for the hardware. For example data arriving on a UART or
a user pressing a button.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 4.1 Awaitable classes

A coro can pause execution by waiting on an ``awaitable`` object. Under CPython
a custom class is made ``awaitable`` by implementing an ``__await__`` special
method. This returns a generator. An ``awaitable`` class is used as follows:

```python
import uasyncio as asyncio

class Foo():
    def __await__(self):
        for n in range(5):
            print('__await__ called')
            yield from asyncio.sleep(1) # Other coros get scheduled here

    __iter__ = __await__  # See note below

async def bar():
    foo = Foo()  # Foo is an awaitable class
    print('waiting for foo')
    await foo
    print('done')

loop = asyncio.get_event_loop()
loop.run_until_complete(bar())
```

Currently MicroPython doesn't support ``__await__`` (issue #2678) and
``__iter__`` must be used. The line ``__iter__ = __await__`` enables portability
between CPython and MicroPython.

Example code may be found in the ``Event`` and ``Barrier`` classes in asyn.py.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 4.2 Asynchronous iterators

These provide a means of returning a finite or infinite sequence of values
and could be used as a means of retrieving successive data items as they arrive
from a read-only device. An asynchronous iterable calls asynchronous code in
its ``next`` method. The class must conform to the following requirements:

 * It has an ``__aiter__`` method defined with  ``async def``and returning the
 asynchronous iterator.
 * It has an `` __anext__`` method which is a coro - i.e. defined with
 ``async def`` and containing at least one ``await`` statement. To stop
 iteration it must raise a ``StopAsyncIteration`` exception.

Successive values are retrieved with ``async for`` as below:

```python
class AsyncIterable:
    def __init__(self):
        self.data = (1, 2, 3, 4, 5)
        self.index = 0

    async def __aiter__(self):
        return self

    async def __anext__(self):
        data = await self.fetch_data()
        if data:
            return data
        else:
            raise StopAsyncIteration

    async def fetch_data(self):
        await asyncio.sleep(0.1)  # Other coros get to run
        if self.index >= len(self.data):
            return None
        x = self.data[self.index]
        self.index += 1
        return x

async def run():
    ai = AsyncIterable()
    async for x in ai:
        print(x)
```

###### [Jump to Contents](./TUTORIAL.md#contents)

## 4.3 Asynchronous context managers

Classes can be designed to support asynchronous context managers. These are CM's
having enter and exit procedures which are coros. An example is the ``Lock``
class described above. This has an ``__aenter__`` coro which is logically
required to run asynchronously. To support the asynchronous CM protocol its
``__aexit__`` method also must be a coro, achieved by including
``await asyncio.sleep(0)``. Such classes are accessed from within a coro with
the following syntax:

```python
async def bar(lock):
    async with lock:
        print('bar acquired lock')
```

As with normal context managers an exit method is guaranteed to be called when
the context manager terminates, whether normally or via an exception. To
achieve this the special methods ``__aenter__`` and ``__aexit__`` must be
defined, both being coros waiting on an ``awaitable`` object. This example comes
from the ``Lock`` class:

```python
    async def __aenter__(self):
        await self.acquire()  # a coro defined with async def

    async def __aexit__(self, *args):
        self.release()  # A conventional method
        await asyncio.sleep_ms(0)
```

Note there is currently a bug in the implementation whereby if an explicit
``return`` is issued within an ``async with`` block, the ``__aexit__`` method
is not called. The solution is to design the code so that in all cases it runs
to completion. The error appears to be in PEP492. See
[this issue](https://github.com/micropython/micropython/issues/3153).

###### [Jump to Contents](./TUTORIAL.md#contents)

## 4.4 Coroutines with timeouts

At the time of writing (12th Nov 2017) this requires PR #3380 and
micropython-lib PR #221 which are yet to be merged.

Timeouts are implemented by means of `uasyncio.wait_for()`. This takes as
arguments a coroutine and a timeout in seconds. If the timeout expires a
`TimeoutError` will be thrown to the coro. The next time the coro is scheduled
for execution the exception will be raised: the coro should trap this and quit.

```python
import uasyncio as asyncio

async def forever():
    print('Starting')
    try:
        while True:
            await asyncio.sleep_ms(300)
            print('Got here')
    except asyncio.TimeoutError:
        print('Got timeout')

async def foo():
    await asyncio.wait_for(forever(), 5)
    await asyncio.sleep(2)

loop = asyncio.get_event_loop()
loop.run_until_complete(foo())
```

Note that if the coro awaits a long delay, it will not be rescheduled until the
time has elapsed. The `TimeoutError` will occur as soon as the coro is
scheduled. But in real time and from the point of view of the calling coro, its
response to the `TimeoutError` will correspondingly be delayed.

###### [Jump to Contents](./TUTORIAL.md#contents)

# 5 Device driver examples

Many devices such as sensors are read-only in nature and need to be polled to
acquire data. In the case of a driver written in Python this must be done by
having a coro which does this periodically. This may present problems if there
is a requirement for rapid polling owing to the round-robin nature of uasyncio
scheduling: the coro will compete for execution with others. There are two
solutions to this. One is to use the experimental version of uasyncio presented
[here](./FASTPOLL.md).

The other potential solution is to delegate the polling to the scheduler using
the IORead mechanism. This is unsupported for Python drivers: see section 5.3.

Note that where a very repeatable polling interval is required, it should be
done using a hardware timer hard interrupt callback. For "very" repeatable read
microsecond level.

In many cases less precise timing is acceptable. The definition of "less" is
application dependent but the latency associated with scheduling the polling
coro is likely to be variable on the order of tens or hundreds of milliseconds.
Latency is determined as follows. When a ``await asyncio.sleep_ms(tim)`` times
out, the coro is scheduled for execution; likewise if tim == 0 or ``yield`` is
issued. It then competes with other coros which have behaved similarly. Since
coros are scheduled in "fair round-robin" fashion you can expect each competing
coro to be scheduled before it.

Each coro will have a worst-case latency which can be calculated by summing,
for every other coro, the worst-case execution time between yielding. This
value also represents the timing uncertainty of the ``sleep_ms()`` function.

[This document](./FASTPOLL.md) describes an experimental version of uasyncio
which offers a means of improving this.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 5.1 The IORead Mechanism

This can be illustrated using a Pyboard UART. The following code sample
demonstrates concurrent I/O on one UART. To run, link Pyboard pins X1 and X2
(UART Txd and Rxd).

```python
import uasyncio as asyncio
from pyb import UART
uart = UART(4, 9600)

async def sender():
    swriter = asyncio.StreamWriter(uart, {})
    while True:
        await swriter.awrite('Hello uart\n')
        await asyncio.sleep(2)

async def receiver():
    sreader = asyncio.StreamReader(uart)
    while True:
        res = await sreader.readline()
        print('Recieved', res)

loop = asyncio.get_event_loop()
loop.create_task(sender())
loop.create_task(receiver())
loop.run_forever()
```

The supporting code may be found in ``__init__.py`` in the uasyncio library.
The mechanism works because the (C) device driver implements the following
methods: ``ioctl``, ``read``, ``write``, ``readline`` and ``close``. See section
5.3 for details of implementing such a device driver in Python (when support
for this becomes available).

###### [Jump to Contents](./TUTORIAL.md#contents)

## 5.2 Using a coro to poll hardware

This is a simple approach, but is only appropriate to hardware which is to be
polled at a relatively low rate. This is for two reasons. Firstly the variable
latency caused by the execution of other coros will result in variable polling
intervals - this may or may not matter depending on the device and application.
Secondly, attempting to poll with a short polling interval may cause the coro
to consume more processor time than is desirable.

The example ``apoll.py`` demonstrates this approach by polling the Pyboard
accelerometer at 100ms intervals. It performs some simple filtering to ignore
noisy samples and prints a message every two seconds if the board is not moved.

Further examples may be found in ``aswitch.py`` which provides drivers for
switch and pushbutton devices.

An example of a driver for a device capable of reading and writing is shown
below. For ease of testing Pyboard UART 4 emulates the notional device. The
driver implements a ``RecordOrientedUart`` class, where data is supplied in
variable length records consisting of bytes instances. The object appends a
delimiter before sending and buffers incoming data until the delimiter is
received. This is a demo and is an inefficient way to use a UART compared to
IORead.

For the purpose of demonstrating asynchronous transmission we assume the
device being emulated has a means of checking that transmission is complete
and that the application requires that we wait on this. Neither assumption is
true in this example but the code fakes it with ``await asyncio.sleep(0.1)``.

Link pins X1 and X2 to run.

```python
import uasyncio as asyncio
from pyb import UART

class RecordOrientedUart():
    DELIMITER = b'\0'
    def __init__(self):
        self.uart = UART(4, 9600)
        self.data = b''

    def __await__(self):
        data = b''
        while not data.endswith(self.DELIMITER):
            yield from asyncio.sleep(0) # Neccessary because:
            while not self.uart.any():
                yield from asyncio.sleep(0) # timing may mean this is never called
            data = b''.join((data, self.uart.read(self.uart.any())))
        self.data = data

    __iter__ = __await__  # workround for issue #2678

    async def send_record(self, data):
        data = b''.join((data, self.DELIMITER))
        self.uart.write(data)
        await self._send_complete()

    # In a real device driver we would poll the hardware
    # for completion in a loop with await asyncio.sleep(0)
    async def _send_complete(self):
        await asyncio.sleep(0.1)

    def read_record(self):  # Synchronous: await the object before calling
        return self.data[0:-1] # Discard delimiter

async def run():
    foo = RecordOrientedUart()
    rx_data = b''
    await foo.send_record(b'A line of text.')
    for _ in range(20):
        await foo  # Other coros are scheduled while we wait
        rx_data = foo.read_record()
        print('Got: {}'.format(rx_data))
        await foo.send_record(rx_data)
        rx_data = b''

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
```

###### [Jump to Contents](./TUTORIAL.md#contents)

## 5.3 Using IORead to poll hardware

The uasyncio ``IORead`` class is provided to support IO to stream devices. It
may be employed by drivers of devices which need to be polled: the polling will
be delegated to the scheduler which uses ``select`` to schedule the first
stream or device driver to be ready. This is more efficient, and offers lower
latency, than running multiple coros each polling a device.

At the time of writing firmware support for using this mechanism in device
drivers written in Python has not been implemented, and the final comment to
[this](https://github.com/micropython/micropython/issues/2664) issue suggests
that it may never be done. So streaming device drivers must be written in C.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 5.4 A complete example: aremote.py

This may be found in the ``nec_ir`` directory. Its use is documented
[here](./nec_ir/README.md). The demo provides a complete device driver example:
a receiver/decoder for an infra red remote controller. The following notes are
salient points regarding its asyncio usage.

A pin interrupt records the time of a state change (in us) and sets an event,
passing the time when the first state change occurred. A coro waits on the
event, yields for the duration of a data burst, then decodes the stored data
before calling a user-specified callback.

Passing the time to the ``Event`` instance enables the coro to compensate for
any asyncio latency when setting its delay period.

###### [Jump to Contents](./TUTORIAL.md#contents)

# 6 Hints and tips

## 6.1 Program hangs

Hanging usually occurs because a task has blocked without yielding: this will
hang the entire system. When developing it is useful to have a coro which
periodically toggles an onboard LED. This provides confirmtion that the
scheduler is running.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 6.2 uasyncio retains state

When running programs using ``uasyncio`` at the REPL, issue a soft reset
(ctrl-D) between runs. This is because ``uasyncio`` retains state between runs
which can lead to confusing behaviour.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 6.3 Garbage Collection

You may want to consider running a coro which issues:

```python
    gc.collect()
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
```

This assumes ``import gc`` has been issued. The purpose of this is discussed
[here](http://docs.micropython.org/en/latest/pyboard/reference/constrained.html)
in the section on the heap.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 6.4 Testing

It's advisable to test that a device driver yields control when you intend it
to. This can be done by running one or more instances of a dummy coro which
runs a loop printing a message, and checking that it runs in the periods when
the driver is blocking:

```python
async def rr(n):
    while True:
        print('Roundrobin ', n)
        await asyncio.sleep(0)
```

As an example of the type of hazard which can occur, in the ``RecordOrientedUart``
example above the ``__await__`` method was originally written as:

```python
    def __await__(self):
        data = b''
        while not data.endswith(self.DELIMITER):
            while not self.uart.any():
                yield from asyncio.sleep(0)
            data = b''.join((data, self.uart.read(self.uart.any())))
        self.data = data
```

In testing this hogged execution until an entire record was received. This was
because ``uart.any()`` always returned a nonzero quantity. By the time it was
called, characters had been received. The solution was to yield execution in
the outer loop:

```python
    def __await__(self):
        data = b''
        while not data.endswith(self.DELIMITER):
            yield from asyncio.sleep(0) # Neccessary because:
            while not self.uart.any():
                yield from asyncio.sleep(0) # timing may mean this is never called
            data = b''.join((data, self.uart.read(self.uart.any())))
        self.data = data
```

It is perhaps worth noting that this error would not have been apparent had
data been sent to the UART at a slow rate rather than via a loopback test.

###### [Jump to Contents](./TUTORIAL.md#contents)

# 7 Notes for beginners

These notes are intended for those unfamiliar with asynchronous code or unsure
of the relative merits of asyncio and the _thread module (i.e. cooperative vs
pre-emptive scheduling).

###### [Jump to Contents](./TUTORIAL.md#contents)

## 7.1 Why Scheduling?

Using a scheduler doesn't enable anything that can't be done with conventional
code. But it does make the solution of certain types of problem simpler to code
and easier to read and maintain.

It facilitates a style of programming based on the concept of routines offering
the illusion of running concurrently. They do this by periodically passing
control to the scheduler which will allow another routine waiting for execution
to run - until it in turn yields control. This can simplify the process of
interacting with physical devices. Consider the task of reading 12
push-buttons. Mechanical switches such as buttons suffer from contact bounce.
This means that several rapidly repeating transitions can occur when the button
is pushed or released.

A simple way to overcome this is as follows. On receipt of the first transition
perform any programmed action. Then wait (typically 50ms) and read the state
of the button. By then the bouncing will be over and its state can be stored to
detect future transitions. Doing this in linear code for 12 buttons can get
messy. If you extend this to support long press or double-click events the code
will get positively convoluted. Using asyncio with the ``aswitch.py`` module we
can write:

```python
async def cb(button_no):  # user code omitted. This runs when
                    # button pressed, with the button number passed

buttons = ('X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8', 'X9', 'X10', 'X11', 'X12')
for button_no, button in enumerate(buttons):
    pb = Pushbutton(Pin(button, Pin.IN, Pin.PULL_UP)
    pb.press_coro(cb, (button_no,))
```

The ``Pushbutton`` class hides the detail, but for each button a coroutine is
created which polls the ``Pin`` object and performs the debouncing. It can also
start user supplied coroutines on button release events, long presses and
double clicks. The code in ``aswitch.py`` achieves this using asyncio.

Scheduling also solves the problem of blocking. If a routine needs to wait for
a physical event to occur before it can continue it is said to be blocked. You
may not want the entire system to be blocked. While this can be solved in
linear code, in threaded code the solution is trivial. The coroutine blocks,
but while it does so it periodically yields execution. Hence the rest of the
system continues to run.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 7.2 Why cooperative rather than pre-emptive?

The initial reaction of beginners to the idea of cooperative multi-tasking is
often one of disappointment. Surely pre-emptive is better? Why should I have to
explicitly yield control when the Python virtual machine can do it for me?

When it comes to embedded systems the cooperative model has two advantages.
Fistly, it is lightweight. It is possible to have large numbers of coroutines
because unlike descheduled threads, paused coroutines contain little state.
Secondly it avoids some of the subtle problems associated with pre-emptive
scheduling. In practice cooperative multi-tasking is widely used, notably in
user interface applications.

To make a case for the defence a pre-emptive model has one advantage: if
someone writes

```python
for x in range(1000000):
    # do something time consuming
```

it won't lock out other threads. Under cooperative schedulers the loop must
explicitly yield control every so many iterations e.g. by putting the code in
a coro and periodically issuing ``await asyncio.sleep(0)``.

Alas this benefit of pre-emption pales into insignificance compared to the
drawbacks. Some of these are covered in the documentation on writing
[interrupt handlers](http://docs.micropython.org/en/latest/reference/isr_rules.html).
In a pre-emptive model every thread can interrupt every other thread, changing
data which might be used in other threads. It is generally much easier to find
and fix a lockup resulting from a coro which fails to yield than locating the
sometimes deeply subtle and rarely occurring bugs which can occur in
pre-emptive code.

To put this in simple terms, if you write a MicroPython coroutine, you can be
sure that variables won't suddenly be changed by another coro: your coro has
complete control until it issues ``await asyncio.sleep(0)``.

Bear in mind that interrupt handlers are pre-emptive.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 7.3 Communication

In non-trivial applications coroutines need to communicate. Conventional Python
techniques can be employed. These include the use of global variables or
declaring coros as object methods: these can then share instance variables.
Alternatively a mutable object may be passed as a coro argument.

Pre-emptive systems mandate specialist classes to achieve "thread safe"
communications; in a cooperative system these are seldom required.

###### [Jump to Contents](./TUTORIAL.md#contents)

## 7.4 Polling

Some hardware devices such as the accelerometer don't support interrupts, and
therefore must be polled (i.e. checked periodically). Polling can also be used
in conjunction with interrupt handlers: the interrupt handler services the
hardware and sets a flag. A coro polls the flag: if it's set it handles the
data and clears the flag.

###### [Jump to Contents](./TUTORIAL.md#contents)

# 8 Modifying uasyncio

The library is designed to be extensible, an example being the
``asyncio_priority`` module. By following the following guidelines a module can
be constructed which alters the functionality of asyncio without the need to
change the official library. Such a module may be used where ``uasyncio`` is
implemented as frozen bytecode.

Assume that the aim is to alter the event loop. The module should issue

```python
from uasyncio import *
```

The event loop should be subclassed from ``PollEventLoop`` (defined in
``__init__.py``).

The event loop is instantiated by the first call to ``get_event_loop()``: this
creates a singleton instance. This is returned by every call to
``get_event_loop()``. On the assumption that the constructor arguments for the
new class differ from those of the base class, the module will need to redefine
``get_event_loop()`` along the following lines:

```python
_event_loop = None  # The singleton instance
_event_loop_class = MyNewEventLoopClass  # The class, not an instance
def get_event_loop(args):
    global _event_loop
    if _event_loop is None:
        _event_loop = _event_loop_class(args)  # Instantiate once only
    return _event_loop
```
