# Application of uasyncio to hardware interfaces

This tutorial is intended for users having varying levels of experience with
asyncio and includes a section for complete beginners.

# Contents

 0. [Introduction](./TUTORIAL.md#0-introduction)  
  0.1 [Installing uasyncio on bare metal](./TUTORIAL.md#01-installing-uasyncio-on-bare-metal)  
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
   3.1.1 [Locks and timeouts](./TUTORIAL.md#311-locks-and-timeouts)  
  3.2 [Event](./TUTORIAL.md#32-event)  
   3.2.1 [The event's value](./TUTORIAL.md#321-the-events-value)  
  3.3 [Barrier](./TUTORIAL.md#33-barrier)  
  3.4 [Semaphore](./TUTORIAL.md#34-semaphore)  
   3.4.1 [BoundedSemaphore](./TUTORIAL.md#341-boundedsemaphore)  
  3.5 [Queue](./TUTORIAL.md#35-queue)  
  3.6 [Other synchronisation primitives](./TUTORIAL.md#36-other-synchronisation-primitives)  
 4. [Designing classes for asyncio](./TUTORIAL.md#4-designing-classes-for-asyncio)  
  4.1 [Awaitable classes](./TUTORIAL.md#41-awaitable-classes)  
   4.1.1 [Use in context managers](./TUTORIAL.md#411-use-in-context-managers)  
   4.1.2 [Awaiting a coro](./TUTORIAL.md#412-awaiting-a-coro)  
  4.2 [Asynchronous iterators](./TUTORIAL.md#42-asynchronous-iterators)  
  4.3 [Asynchronous context managers](./TUTORIAL.md#43-asynchronous-context-managers)  
 5. [Exceptions timeouts and cancellation](./TUTORIAL.md#5-exceptions-timeouts-and-cancellation)  
  5.1 [Exceptions](./TUTORIAL.md#51-exceptions)  
  5.2 [Cancellation and Timeouts](./TUTORIAL.md#52-cancellation-and-timeouts)  
   5.2.1 [Task cancellation](./TUTORIAL.md#521-task-cancellation)  
   5.2.2 [Coroutines with timeouts](./TUTORIAL.md#522-coroutines-with-timeouts)  
 6. [Interfacing hardware](./TUTORIAL.md#6-interfacing-hardware)  
  6.1 [Timing issues](./TUTORIAL.md#61-timing-issues)  
  6.2 [Polling hardware with a coroutine](./TUTORIAL.md#62-polling-hardware-with-a-coroutine)  
  6.3 [Using the stream mechanism](./TUTORIAL.md#63-using-the-stream-mechanism)  
   6.3.1 [A UART driver example](./TUTORIAL.md#631-a-uart-driver-example)  
  6.4 [Writing streaming device drivers](./TUTORIAL.md#64-writing-streaming-device-drivers)  
  6.5 [A complete example: aremote.py](./TUTORIAL.md#65-a-complete-example-aremotepy)
  A driver for an IR remote control receiver.  
  6.6 [Driver for HTU21D](./TUTORIAL.md#66-htu21d-environment-sensor) A
  temperature and humidity sensor.  
 7. [Hints and tips](./TUTORIAL.md#7-hints-and-tips)  
  7.1 [Program hangs](./TUTORIAL.md#71-program-hangs)  
  7.2 [uasyncio retains state](./TUTORIAL.md#72-uasyncio-retains-state)  
  7.3 [Garbage Collection](./TUTORIAL.md#73-garbage-collection)  
  7.4 [Testing](./TUTORIAL.md#74-testing)  
  7.5 [A common error](./TUTORIAL.md#75-a-common-error) This can be hard to find.  
  7.6 [Socket programming](./TUTORIAL.md#76-socket-programming)  
   7.6.1 [WiFi issues](./TUTORIAL.md#761-wifi-issues)  
  7.7 [Event loop constructor args](./TUTORIAL.md#77-event-loop-constructor-args)  
 8. [Notes for beginners](./TUTORIAL.md#8-notes-for-beginners)  
  8.1 [Problem 1: event loops](./TUTORIAL.md#81-problem-1:-event-loops)  
  8.2 [Problem 2: blocking methods](./TUTORIAL.md#8-problem-2:-blocking-methods)  
  8.3 [The uasyncio approach](./TUTORIAL.md#83-the-uasyncio-approach)  
  8.4 [Scheduling in uasyncio](./TUTORIAL.md#84-scheduling-in-uasyncio)  
  8.5 [Why cooperative rather than pre-emptive?](./TUTORIAL.md#85-why-cooperative-rather-than-pre-emptive)  
  8.6 [Communication](./TUTORIAL.md#86-communication)  
  8.7 [Polling](./TUTORIAL.md#87-polling)  

###### [Main README](./README.md)

# 0. Introduction

Most of this document assumes some familiarity with asynchronous programming.
For those new to it an introduction may be found
[in section 7](./TUTORIAL.md#8-notes-for-beginners).

The MicroPython `uasyncio` library comprises a subset of Python's `asyncio`
library. It is designed for use on microcontrollers. As such it has a small RAM
footprint and fast context switching with zero RAM allocation. This document
describes its use with a focus on interfacing hardware devices. The aim is to
design drivers in such a way that the application continues to run while the
driver is awaiting a response from the hardware. The application remains
responsive to events and to user interaction.

Another major application area for asyncio is in network programming: many
guides to this may be found online.

Note that MicroPython is based on Python 3.4 with minimal Python 3.5 additions.
Except where detailed below, `asyncio` features of versions >3.4 are
unsupported. As stated above it is a subset; this document identifies supported
features.

This tutorial aims to present a consistent programming style compatible with
CPython V3.5 and above.

## 0.1 Installing uasyncio on bare metal

It is recommended to use MicroPython firmware V1.11 or later. On many platforms
no installation is necessary as `uasyncio` is compiled into the build. Test by
issuing
```python
import uasyncio
```
at the REPL.

The following instructions cover cases where modules are not pre-installed. The
`queues` and `synchro` modules are optional, but are required to run all the
examples below.

#### Hardware with internet connectivity

On hardware with an internet connection and running firmware V1.11 or greater
installation may be done using `upip`, which is pre-installed. After ensuring
that the device is connected to your network issue:
```python
import upip
upip.install('micropython-uasyncio')
upip.install('micropython-uasyncio.synchro')
upip.install('micropython-uasyncio.queues')
```
Error meesages from `upip` are not too helpful. If you get an obscure error,
double check your internet connection.

#### Hardware without internet connectivity (micropip)

On hardware which lacks an internet connection (such as a Pyboard V1.x) the
easiest way is to run `micropip.py` on a PC to install to a directory of your
choice, then to copy the resultant directory structure to the target hardware.
The `micropip.py` utility runs under Python 3.2 or above and runs under Linux,
Windows and OSX. It may be found
[here](https://github.com/peterhinch/micropython-samples/tree/master/micropip).

Typical invocation:
```bash
$ micropip.py install -p ~/rats micropython-uasyncio
$ micropip.py install -p ~/rats micropython-uasyncio.synchro
$ micropip.py install -p ~/rats micropython-uasyncio.queues
```

#### Hardware without internet connectivity (copy source)

If `micropip.py` is not to be used the files should be copied from source. The
following instructions describe copying the bare minimum of files to a target
device, also the case where `uasyncio` is to be frozen into a compiled build as
bytecode. For the latest release compatible with official firmware
files must be copied from the official
[micropython-lib](https://github.com/micropython/micropython-lib).

Clone the library to a PC with
```bash
$ git clone https://github.com/micropython/micropython-lib.git
```
On the target hardware create a `uasyncio` directory (optionally under a
directory `lib`) and copy the following files to it:
 * `uasyncio/uasyncio/__init__.py`
 * `uasyncio.core/uasyncio/core.py`
 * `uasyncio.synchro/uasyncio/synchro.py`
 * `uasyncio.queues/uasyncio/queues.py`

The `uasyncio` modules may be frozen as bytecode in the usual way, by placing
the `uasyncio` directory and its contents in the port's `modules` directory and
rebuilding.

###### [Main README](./README.md)

# 1. Cooperative scheduling

The technique of cooperative multi-tasking is widely used in embedded systems.
It offers lower overheads than pre-emptive scheduling and avoids many of the
pitfalls associated with truly asynchronous threads of execution.

###### [Contents](./TUTORIAL.md#contents)

## 1.1 Modules

The following modules are provided which may be copied to the target hardware.

**Libraries**

 1. [asyn.py](./asyn.py) Provides synchronisation primitives `Lock`, `Event`,
 `Barrier`, `Semaphore`, `BoundedSemaphore`, `Condition` and `gather`. Provides
 support for task cancellation via `NamedTask` and `Cancellable` classes.
 2. [aswitch.py](./aswitch.py) Provides classes for interfacing switches and
 pushbuttons and also a software retriggerable delay object. Pushbuttons are a
 generalisation of switches providing logical rather than physical status along
 with double-clicked and long pressed events.

**Demo Programs**

The first two are the most immediately rewarding as they produce visible
results by accessing Pyboard hardware.

 1. [aledflash.py](./aledflash.py) Flashes the four Pyboard LEDs asynchronously
 for 10s. The simplest uasyncio demo. Import it to run.
 2. [apoll.py](./apoll.py) A device driver for the Pyboard accelerometer.
 Demonstrates the use of a coroutine to poll a device. Runs for 20s. Import it
 to run. Requires a Pyboard V1.x.
 3. [astests.py](./astests.py) Test/demonstration programs for the
 [aswitch](./aswitch) module.
 4. [asyn_demos.py](./asyn_demos.py) Simple task cancellation demos.
 5. [roundrobin.py](./roundrobin.py) Demo of round-robin scheduling. Also a
 benchmark of scheduling performance.
 6. [awaitable.py](./awaitable.py) Demo of an awaitable class. One way of
 implementing a device driver which polls an interface.
 7. [chain.py](./chain.py) Copied from the Python docs. Demo of chaining
 coroutines.
 8. [aqtest.py](./aqtest.py) Demo of uasyncio `Queue` class.
 9. [aremote.py](./aremote.py) Example device driver for NEC protocol IR remote
 control.
 10. [auart.py](./auart.py) Demo of streaming I/O via a Pyboard UART.
 11. [auart_hd.py](./auart_hd.py) Use of the Pyboard UART to communicate with a
 device using a half-duplex protocol. Suits devices such as those using the
 'AT' modem command set.
 12. [iorw.py](./iorw.py) Demo of a read/write device driver using the stream
 I/O mechanism.

**Test Programs**

 1. [asyntest.py](./asyntest.py) Tests for the synchronisation primitives in
 [asyn.py](./asyn.py).
 2. [cantest.py](./cantest.py) Task cancellation tests.

**Utility**

 1. [check_async_code.py](./check_async_code.py) A Python3 utility to locate a
 particular coding error which can be hard to find. See
 [para 7.5](./TUTORIAL.md#75-a-common-error).

**Benchmarks**

The `benchmarks` directory contains scripts to test and characterise the
uasyncio scheduler. See [this doc](./FASTPOLL.md).

###### [Contents](./TUTORIAL.md#contents)

# 2. uasyncio

The asyncio concept is of cooperative multi-tasking based on coroutines,
referred to in this document as coros or tasks.

###### [Contents](./TUTORIAL.md#contents)

## 2.1 Program structure: the event loop

Consider the following example:

```python
import uasyncio as asyncio
async def bar():
    count = 0
    while True:
        count += 1
        print(count)
        await asyncio.sleep(1)  # Pause 1s

loop = asyncio.get_event_loop()
loop.create_task(bar()) # Schedule ASAP
loop.run_forever()
```

Program execution proceeds normally until the call to `loop.run_forever`. At
this point execution is controlled by the scheduler. A line after
`loop.run_forever` would never be executed. The scheduler runs `bar`
because this has been placed on the scheduler's queue by `loop.create_task`.
In this trivial example there is only one coro: `bar`. If there were others,
the scheduler would schedule them in periods when `bar` was paused.

Most embedded applications have an event loop which runs continuously. The event
loop can also be started in a way which permits termination, by using the event
loop's `run_until_complete` method; this is mainly of use in testing. Examples
may be found in the [astests.py](./astests.py) module.

The event loop instance is a singleton, instantiated by a program's first call
to `asyncio.get_event_loop()`. This takes two optional integer args being the
lengths of the two coro queues. Typically both will have the same value being
at least the number of concurrent coros in the application. The default of 16
is usually sufficient. If using non-default values see
[Event loop constructor args](./TUTORIAL.md#77-event-loop-constructor-args).

If a coro needs to call an event loop method (usually `create_task`), calling
`asyncio.get_event_loop()` (without args) will efficiently return it.

###### [Contents](./TUTORIAL.md#contents)

## 2.2 Coroutines (coros)

A coro is instantiated as follows:

```python
async def foo(delay_secs):
    await asyncio.sleep(delay_secs)
    print('Hello')
```

A coro can allow other coroutines to run by means of the `await coro`
statement. A coro usually contains a `await` statement. The `await` causes 
the called `coro` to run to completion before execution passes to the next
instruction.

Consider these lines of code:

```python
await asyncio.sleep(delay_secs)
await asyncio.sleep(0)
```

The first causes the code to pause for the duration of the delay, with other
coros being scheduled for the duration. A delay of 0 causes any pending coros
to be scheduled in round-robin fashion before the following line is run. See
the `roundrobin.py` example.

###### [Contents](./TUTORIAL.md#contents)

### 2.2.1 Queueing a coro for scheduling

 * `EventLoop.create_task` Arg: the coro to run. The scheduler queues the
 coro to run ASAP. The `create_task` call returns immediately. The coro
 arg is specified with function call syntax with any required arguments passed.
 * `EventLoop.run_until_complete` Arg: the coro to run. The scheduler queues
 the coro to run ASAP. The coro arg is specified with function call syntax with
 any required arguments passed. The `run_until_complete` call returns when
 the coro terminates: this method provides a way of quitting the scheduler.
 * `await`  Arg: the coro to run, specified with function call syntax. Starts
 the coro ASAP. The awaiting coro blocks until the awaited one has run to
 completion.

The above are compatible with CPython. Additional uasyncio methods are
discussed in 2.2.3 below.

###### [Contents](./TUTORIAL.md#contents)

### 2.2.2 Running a callback function

Callbacks should be Python functions designed to complete in a short period of
time. This is because coroutines will have no opportunity to run for the
duration.

The following `EventLoop` methods schedule callbacks:

 1. `call_soon` Call as soon as possible. Args: `callback` the callback to
 run, `*args` any positional args may follow separated by commas.
 2. `call_later` Call after a delay in secs. Args: `delay`, `callback`,
 `*args`
 3. `call_later_ms` Call after a delay in ms. Args: `delay`, `callback`,
 `*args`.

```python
loop = asyncio.get_event_loop()
loop.call_soon(foo, 5) # Schedule callback 'foo' ASAP with an arg of 5.
loop.call_later(2, foo, 5) # Schedule after 2 seconds.
loop.call_later_ms(50, foo, 5) # Schedule after 50ms.
loop.run_forever()
```

###### [Contents](./TUTORIAL.md#contents)

### 2.2.3 Notes

A coro can contain a `return` statement with arbitrary return values. To
retrieve them issue:

```python
result = await my_coro()
```

Coros may be bound methods. A coro must contain at least one `await` statement.

###### [Contents](./TUTORIAL.md#contents)

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
this is discussed further in [Section 6](./TUTORIAL.md#6-interfacing-hardware).

Very precise delays may be issued by using the `utime` functions `sleep_ms`
and `sleep_us`. These are best suited for short delays as the scheduler will
be unable to schedule other coros while the delay is in progress.

###### [Contents](./TUTORIAL.md#contents)

# 3 Synchronisation

There is often a need to provide synchronisation between coros. A common
example is to avoid what are known as "race conditions" where multiple coros
compete to access a single resource. An example is provided in the
[astests.py](./astests.py) program and discussed in [the docs](./DRIVERS.md).
Another hazard is the "deadly embrace" where two coros each wait on the other's
completion.

In simple applications communication may be achieved with global flags or bound
variables. A more elegant approach is to use synchronisation primitives. The
module
[asyn.py](https://github.com/peterhinch/micropython-async/blob/master/asyn.py)
offers "micro" implementations of `Event`, `Barrier`, `Semaphore` and
`Condition` primitives. These are for use only with asyncio. They are not
thread safe and should not be used with the `_thread` module or from an
interrupt handler except where mentioned. A `Lock` primitive is provided which
is an alternative to the official implementation.

Another synchronisation issue arises with producer and consumer coros. The
producer generates data which the consumer uses. Asyncio provides the `Queue`
object. The producer puts data onto the queue while the consumer waits for its
arrival (with other coros getting scheduled for the duration). The `Queue`
guarantees that items are removed in the order in which they were received.
Alternatively a `Barrier` instance can be used if the producer must wait
until the consumer is ready to access the data.

The following provides a brief overview of the primitives. Full documentation
may be found [here](./PRIMITIVES.md).

###### [Contents](./TUTORIAL.md#contents)

## 3.1 Lock

This describes the use of the official `Lock` primitive.

This guarantees unique access to a shared resource. In the following code
sample a `Lock` instance `lock` has been created and is passed to all coros
wishing to access the shared resource. Each coro attempts to acquire the lock,
pausing execution until it succeeds.

```python
import uasyncio as asyncio
from uasyncio.synchro import Lock

async def task(i, lock):
    while 1:
        await lock.acquire()
        print("Acquired lock in task", i)
        await asyncio.sleep(0.5)
        lock.release()

async def killer():
    await asyncio.sleep(10)

loop = asyncio.get_event_loop()

lock = Lock()  # The global Lock instance

loop.create_task(task(1, lock))
loop.create_task(task(2, lock))
loop.create_task(task(3, lock))

loop.run_until_complete(killer())  # Run for 10s
```

### 3.1.1 Locks and timeouts

At time of writing (5th Jan 2018) the official `Lock` class is not complete.
If a coro is subject to a [timeout](./TUTORIAL.md#522-coroutines-with-timeouts)
and the timeout is triggered while it is waiting on a lock, the timeout will be
ineffective. It will not receive the `TimeoutError` until it has acquired the
lock. The same observation applies to task cancellation.

The module [asyn.py](./asyn.py) offers a `Lock` class which works in these
situations [see docs](./PRIMITIVES.md#32-class-lock). It is significantly less
efficient than the official class but supports additional interfaces as per the
CPython version including context manager usage.

###### [Contents](./TUTORIAL.md#contents)

## 3.2 Event

This provides a way for one or more coros to pause until another flags them to
continue. An `Event` object is instantiated and made accessible to all coros
using it:

```python
import asyn
event = asyn.Event()
```

Coros waiting on the event issue `await event` whereupon execution pauses until
another issues `event.set()`. [Full details.](./PRIMITIVES.md#33-class-event)

This presents a problem if `event.set()` is issued in a looping construct; the
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

Where multiple coros wait on a single event synchronisation can be achieved by
means of an acknowledge event. Each coro needs a separate event.

```python
async def eventwait(event, ack_event):
    await event
    ack_event.set()
```

An example of this is provided in the `event_test` function in `asyntest.py`.
This is cumbersome. In most cases - even those with a single waiting coro - the
Barrier class below offers a simpler approach.

An Event can also provide a means of communication between an interrupt handler
and a coro. The handler services the hardware and sets an event which is tested
in slow time by the coro.

###### [Contents](./TUTORIAL.md#contents)

### 3.2.1 The event's value

The `event.set()` method can accept an optional data value of any type. A
coro waiting on the event can retrieve it by means of `event.value()`. Note
that `event.clear()` will set the value to `None`. A typical use for this
is for the coro setting the event to issue `event.set(utime.ticks_ms())`. Any
coro waiting on the event can determine the latency incurred, for example to
perform compensation for this.

###### [Contents](./TUTORIAL.md#contents)

## 3.3 Barrier

This has two uses. Firstly it can cause a coro to pause until one or more other
coros have terminated.

Secondly it enables multiple coros to rendezvous at a particular point. For
example producer and consumer coros can synchronise at a point where the
producer has data available and the consumer is ready to use it. At that point
in time the `Barrier` can run an optional callback before the barrier is
released and all waiting coros can continue. [Full details.](./PRIMITIVES.md#34-class-barrier)

The callback can be a function or a coro. In most applications a function is
likely to be used: this can be guaranteed to run to completion before the
barrier is released.

An example is the `barrier_test` function in `asyntest.py`. In the code
fragment from that program:

```python
import asyn

def callback(text):
    print(text)

barrier = asyn.Barrier(3, callback, ('Synch',))

async def report():
    for i in range(5):
        print('{} '.format(i), end='')
        await barrier
```

multiple instances of `report` print their result and pause until the other
instances are also complete and waiting on `barrier`. At that point the
callback runs. On its completion the coros resume.

###### [Contents](./TUTORIAL.md#contents)

## 3.4 Semaphore

A semaphore limits the number of coros which can access a resource. It can be
used to limit the number of instances of a particular coro which can run
concurrently. It performs this using an access counter which is initialised by
the constructor and decremented each time a coro acquires the semaphore.
[Full details.](./PRIMITIVES.md#35-class-semaphore)

The easiest way to use it is with a context manager:

```python
import asyn
sema = asyn.Semaphore(3)
async def foo(sema):
    async with sema:
        # Limited access here
```
An example is the `semaphore_test` function in `asyntest.py`.

###### [Contents](./TUTORIAL.md#contents)

### 3.4.1 BoundedSemaphore

This works identically to the `Semaphore` class except that if the `release`
method causes the access counter to exceed its initial value, a `ValueError`
is raised. [Full details.](./PRIMITIVES.md#351-class-boundedsemaphore)

###### [Contents](./TUTORIAL.md#contents)

## 3.5 Queue

The `Queue` class is officially supported and the sample program `aqtest.py`
demonstrates its use. A queue is instantiated as follows:

```python
from uasyncio.queues import Queue
q = Queue()
```

A typical producer coro might work as follows:

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

The `Queue` class provides significant additional functionality in that the
size of queues may be limited and the status may be interrogated. The behaviour
on empty status and (where size is limited) the behaviour on full status may be
controlled. Documentation of this is in the code.

###### [Contents](./TUTORIAL.md#contents)

## 3.6 Other synchronisation primitives

The [asyn.py](./asyn.py) library provides 'micro' implementations of CPython
capabilities, namely the [Condition class](./PRIMITIVES.md#36-class-condition)
and the [gather](./PRIMITIVES.md#37-class-gather) method.

The `Condition` class enables a coro to notify other coros which are waiting on
a locked resource. Once notified they will access the resource and release the
lock in turn. The notifying coro can limit the number of coros to be notified.

The CPython `gather` method enables a list of coros to be launched. When the
last has completed a list of results is returned. This 'micro' implementation
uses different syntax. Timeouts may be applied to any of the coros.

###### [Contents](./TUTORIAL.md#contents)

# 4 Designing classes for asyncio

In the context of device drivers the aim is to ensure nonblocking operation.
The design should ensure that other coros get scheduled in periods while the
driver is waiting for the hardware. For example a task awaiting data arriving
on a UART or a user pressing a button should allow other coros to be scheduled
until the event occurs..

###### [Contents](./TUTORIAL.md#contents)

## 4.1 Awaitable classes

A coro can pause execution by waiting on an `awaitable` object. Under CPython
a custom class is made `awaitable` by implementing an `__await__` special
method. This returns a generator. An `awaitable` class is used as follows:

```python
import uasyncio as asyncio

class Foo():
    def __await__(self):
        for n in range(5):
            print('__await__ called')
            yield from asyncio.sleep(1) # Other coros get scheduled here
        return 42

    __iter__ = __await__  # See note below

async def bar():
    foo = Foo()  # Foo is an awaitable class
    print('waiting for foo')
    res = await foo  # Retrieve result
    print('done', res)

loop = asyncio.get_event_loop()
loop.run_until_complete(bar())
```

Currently MicroPython doesn't support `__await__` 
[issue #2678](https://github.com/micropython/micropython/issues/2678) and
`__iter__` must be used. The line `__iter__ = __await__` enables portability
between CPython and MicroPython. Example code may be found in the `Event`,
`Barrier`, `Cancellable` and `Condition` classes in [asyn.py](./asyn.py).

### 4.1.1 Use in context managers

Awaitable objects can be used in synchronous or asynchronous CM's by providing
the necessary special methods. The syntax is:

```python
with await awaitable as a:  # The 'as' clause is optional
    # code omitted
async with awaitable as a:  # Asynchronous CM (see below)
    # do something
```

To achieve this the `__await__` generator should return `self`. This is passed
to any variable in an `as` clause and also enables the special methods to work.
See `asyn.Condition` and `asyntest.condition_test`, where the `Condition` class
is awaitable and may be used in a synchronous CM.

###### [Contents](./TUTORIAL.md#contents)

### 4.1.2 Awaiting a coro

The Python language requires that `__await__` is a generator function. In
MicroPython generators and coroutines are identical, so the solution is to use
`yield from coro(args)`.

This tutorial aims to offer code portable to CPython 3.5 or above. In CPython
coroutines and generators are distinct. CPython coros have an `__await__`
special method which retrieves a generator. This is portable:

```python
up = False  # Running under MicroPython?
try:
    import uasyncio as asyncio
    up = True  # Or can use sys.implementation.name
except ImportError:
    import asyncio

async def times_two(n):  # Coro to await
    await asyncio.sleep(1)
    return 2 * n

class Foo():
    def __await__(self):
        res = 1
        for n in range(5):
            print('__await__ called')
            if up:  # MicroPython
                res = yield from times_two(res)
            else:  # CPython
                res = yield from times_two(res).__await__()
        return res

    __iter__ = __await__

async def bar():
    foo = Foo()  # foo is awaitable
    print('waiting for foo')
    res = await foo  # Retrieve value
    print('done', res)

loop = asyncio.get_event_loop()
loop.run_until_complete(bar())
```

Note that, in `__await__`, `yield from asyncio.sleep(1)` is allowed by CPython.
I haven't yet established how this is achieved.

###### [Contents](./TUTORIAL.md#contents)

## 4.2 Asynchronous iterators

These provide a means of returning a finite or infinite sequence of values
and could be used as a means of retrieving successive data items as they arrive
from a read-only device. An asynchronous iterable calls asynchronous code in
its `next` method. The class must conform to the following requirements:

 * It has an `__aiter__` method defined with  `async def`and returning the
 asynchronous iterator.
 * It has an ` __anext__` method which is a coro - i.e. defined with
 `async def` and containing at least one `await` statement. To stop
 iteration it must raise a `StopAsyncIteration` exception.

Successive values are retrieved with `async for` as below:

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

###### [Contents](./TUTORIAL.md#contents)

## 4.3 Asynchronous context managers

Classes can be designed to support asynchronous context managers. These are CM's
having enter and exit procedures which are coros. An example is the `Lock`
class described above. This has an `__aenter__` coro which is logically
required to run asynchronously. To support the asynchronous CM protocol its
`__aexit__` method also must be a coro, achieved by including
`await asyncio.sleep(0)`. Such classes are accessed from within a coro with
the following syntax:

```python
async def bar(lock):
    async with lock:
        print('bar acquired lock')
```

As with normal context managers an exit method is guaranteed to be called when
the context manager terminates, whether normally or via an exception. To
achieve this the special methods `__aenter__` and `__aexit__` must be
defined, both being coros waiting on a coro or `awaitable` object. This example
comes from the `Lock` class:

```python
    async def __aenter__(self):
        await self.acquire()  # a coro defined with async def
        return self

    async def __aexit__(self, *args):
        self.release()  # A conventional method
        await asyncio.sleep_ms(0)
```

If the `async with` has an `as variable` clause the variable receives the
value returned by `__aenter__`.

To ensure correct behaviour firmware should be V1.9.10 or later.

###### [Contents](./TUTORIAL.md#contents)

# 5 Exceptions timeouts and cancellation

These topics are related: `uasyncio` enables the cancellation of tasks, and the
application of a timeout to a task, by throwing an exception to the task in a
special way.

## 5.1 Exceptions

Where an exception occurs in a coro, it should be trapped either in that coro
or in a coro which is awaiting its completion. This ensures that the exception
is not propagated to the scheduler. If this occurred the scheduler would stop
running, passing the exception to the code which started the scheduler.
Consequently, to avoid stopping the scheduler, coros launched with
`loop.create_task()` must trap any exceptions internally.

Using `throw` or `close` to throw an exception to a coro is unwise. It subverts
`uasyncio` by forcing the coro to run, and possibly terminate, when it is still
queued for execution.

There is a "gotcha" illustrated by this code sample. If allowed to run to
completion it works as expected.

```python
import uasyncio as asyncio
async def foo():
    await asyncio.sleep(3)
    print('About to throw exception.')
    1/0

async def bar():
    try:
        await foo()
    except ZeroDivisionError:
        print('foo was interrupted by zero division')  # Happens
        raise  # Force shutdown to run by propagating to loop.
    except KeyboardInterrupt:
        print('foo was interrupted by ctrl-c')  # NEVER HAPPENS
        raise

async def shutdown():
    print('Shutdown is running.')  # Happens in both cases
    await asyncio.sleep(1)
    print('done')

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(bar())
except ZeroDivisionError:
    loop.run_until_complete(shutdown())
except KeyboardInterrupt:
    print('Keyboard interrupt at loop level.')
    loop.run_until_complete(shutdown())
```

However issuing a keyboard interrupt causes the exception to go to the event
loop. This is because `uasyncio.sleep` causes execution to be transferred to
the event loop. Consequently applications requiring cleanup code in response to
a keyboard interrupt should trap the exception at the event loop level.

###### [Contents](./TUTORIAL.md#contents)

## 5.2 Cancellation and Timeouts

As stated above, these features work by throwing an exception to a task in a
special way, using a MicroPython specific coro method `pend_throw`. The way
this works is version dependent. In official `uasyncio` V2.0 the exception is
not processed until the task is next scheduled. This imposes latency if the
task is waiting on a `sleep` or on I/O. Timeouts may extend beyond their
nominal period. Task cancelling other tasks cannot determine when cancellation
is complete.

There is currently a wokround and two solutions.
 * Workround: the `asyn` library provides means of waiting on cancellation of
 tasks or groups of tasks. See [Task Cancellation](./PRIMITIVES.md#4-task-cancellation).
 * [Paul Sokolovsky's library fork](https://github.com/pfalcon/micropython-lib)
 provides `uasyncio` V2.4, but this requires his
 [Pycopy](https://github.com/pfalcon/micropython) firmware.
 * The [fast_io](./FASTPOLL.md) fork of `uasyncio` solves this in Python (in a
 less elegant manner) and runs under official firmware.

The exception hierarchy used here is `Exception-CancelledError-TimeoutError`.

## 5.2.1 Task cancellation

`uasyncio` provides a `cancel(coro)` function. This works by throwing an
exception to the coro using `pend_throw`. This works with nested coros. Usage
is as follows:
```python
async def foo():
    while True:
        # do something every 10 secs
        await asyncio.sleep(10)

async def bar(loop):
    foo_instance = foo()  # Create a coroutine instance
    loop.create_task(foo_instance)
    # code omitted
    asyncio.cancel(foo_instance)
```
If this example is run against `uasyncio` V2.0, when `bar` issues `cancel` it
will not take effect until `foo` is next scheduled. There is thus a latency of
up to 10s in the cancellation of `foo`. Another source of latency would arise
if `foo` waited on I/O. Where latency arises, `bar` cannot determine whether
`foo` has yet been cancelled. This matters in some use-cases.

Using the Paul Sokolovsky fork or `fast_io` a simple `sleep(0)` suffices:
```python
async def foo():
    while True:
        # do something every 10 secs
        await asyncio.sleep(10)

async def bar(loop):
    foo_instance = foo()  # Create a coroutine instance
    loop.create_task(foo_instance)
    # code omitted
    asyncio.cancel(foo_instance)
    await asyncio.sleep(0)
    # Task is now cancelled
```
This would also work in `uasyncio` V2.0 if `foo` (and any coros awaited by
`foo`) never issued `sleep` or waited on I/O.

Behaviour which may surprise the unwary arises when a coro to be cancelled is
awaited rather than being launched by `create_task`. Consider this fragment:

```python
async def foo():
    while True:
        # do something every 10 secs
        await asyncio.sleep(10)

async def foo_runner(foo_instance):
    await foo_instance
    print('This will not be printed')

async def bar(loop):
    foo_instance = foo()
    loop.create_task(foo_runner(foo_instance))
    # code omitted
    asyncio.cancel(foo_instance)
```
When `foo` is cancelled it is removed from the scheduler's queue; because it
lacks a `return` statement the calling routine `foo_runner` never resumes. It
is recommended always to trap the exception in the outermost scope of a
function subject to cancellation:
```python
async def foo():
    try:
        while True:
            await asyncio.sleep(10)
            await my_coro
    except asyncio.CancelledError:
        return
```
In this instance `my_coro` does not need to trap the exception as it will be
propagated to the calling coro and trapped there.

**Note** It is bad practice to issue the `close` or `throw` methods of a
de-scheduled coro. This subverts the scheduler by causing the coro to execute
code even though descheduled. This is likely to have unwanted consequences.

###### [Contents](./TUTORIAL.md#contents)

## 5.2.2 Coroutines with timeouts

Timeouts are implemented by means of `uasyncio` methods `.wait_for()` and
`.wait_for_ms()`. These take as arguments a coroutine and a timeout in seconds
or ms respectively. If the timeout expires a `TimeoutError` will be thrown to
the coro using `pend_throw`. This exception must be trapped, either by the coro
or its caller. This is for the reason discussed above: if a coro times out it
is descheduled. Unless it traps the error and returns the only way the caller
can proceed is by trapping the exception itself.

Where the exception is trapped by the coro, I have experienced obscure failures
if the exception is not trapped in the outermost scope as below:
```python
import uasyncio as asyncio

async def forever():
    try:
        print('Starting')
        while True:
            await asyncio.sleep_ms(300)
            print('Got here')
    except asyncio.TimeoutError:
        print('Got timeout')  # And return

async def foo():
    await asyncio.wait_for(forever(), 5)
    await asyncio.sleep(2)

loop = asyncio.get_event_loop()
loop.run_until_complete(foo())
```
Alternatively it may be trapped by the caller:
```python
import uasyncio as asyncio

async def forever():
    print('Starting')
    while True:
        await asyncio.sleep_ms(300)
        print('Got here')

async def foo():
    try:
        await asyncio.wait_for(forever(), 5)
    except asyncio.TimeoutError:
        pass
    print('Timeout elapsed.')
    await asyncio.sleep(2)

loop = asyncio.get_event_loop()
loop.run_until_complete(foo())
```

#### Uasyncio V2.0 note

This does not apply to the Paul Sokolovsky fork or to `fast_io`.

If the coro issues `await asyncio.sleep(t)` where `t` is a long delay, the coro
will not be rescheduled until `t` has elapsed. If the timeout has elapsed
before the `sleep` is complete the `TimeoutError` will occur when the coro is
scheduled - i.e. when `t` has elapsed. In real time and from the point of view
of the calling coro, its response to the `TimeoutError` will be delayed.

If this matters to the application, create a long delay by awaiting a short one
in a loop. The coro `asyn.sleep` [supports this](./PRIMITIVES.md#41-coro-sleep).

###### [Contents](./TUTORIAL.md#contents)

# 6 Interfacing hardware

At heart all interfaces between `uasyncio` and external asynchronous events
rely on polling. Hardware requiring a fast response may use an interrupt. But
the interface between the interrupt service routine (ISR) and a user coro will
be polled. For example the ISR might trigger an `Event` or set a global flag,
while a coroutine awaiting the outcome polls the object each time it is
scheduled.

Polling may be effected in two ways, explicitly or implicitly. The latter is
performed by using the `stream I/O` mechanism which is a system designed for
stream devices such as UARTs and sockets. At its simplest explicit polling may
consist of code like this:

```python
async def poll_my_device():
    global my_flag  # Set by device ISR
    while True:
        if my_flag:
            my_flag = False
            # service the device
        await asyncio.sleep(0)
```

In place of a global, an instance variable, an `Event` object or an instance of
an awaitable class might be used. Explicit polling is discussed
further [below](./TUTORIAL.md#62-polling-hardware-with-a-coroutine).

Implicit polling consists of designing the driver to behave like a stream I/O
device such as a socket or UART, using `stream I/O`. This polls devices using
Python's `select.poll` system: because the polling is done in C it is faster
and more efficient than explicit polling. The use of `stream I/O` is discussed
[here](./TUTORIAL.md#63-using-the-stream-mechanism).

Owing to its efficiency implicit polling benefits most fast I/O device drivers:
streaming drivers can be written for many devices not normally considered as
streaming devices [section 6.4](./TUTORIAL.md#64-writing-streaming-device-drivers).

###### [Contents](./TUTORIAL.md#contents)

## 6.1 Timing issues

Both explicit and implicit polling are currently based on round-robin
scheduling. Assume I/O is operating concurrently with N user coros each of
which yields with a zero delay. When I/O has been serviced it will next be
polled once all user coros have been scheduled. The implied latency needs to be
considered in the design. I/O channels may require buffering, with an ISR
servicing the hardware in real time from buffers and coroutines filling or
emptying the buffers in slower time.

The possibility of overrun also needs to be considered: this is the case where
something being polled by a coroutine occurs more than once before the coro is
actually scheduled.

Another timing issue is the accuracy of delays. If a coro issues

```python
    await asyncio.sleep_ms(t)
    # next line
```

the scheduler guarantees that execution will pause for at least `t`ms. The
actual delay may be greater depending on the system state when `t` expires.
If, at that time, all other coros are waiting on nonzero delays, the next line
will immediately be scheduled. But if other coros are pending execution (either
because they issued a zero delay or because their time has also elapsed) they
may be scheduled first. This introduces a timing uncertainty into the `sleep()`
and `sleep_ms()` functions. The worst-case value for this overrun may be
calculated by summing, for every other coro, the worst-case execution time
between yielding to the scheduler.

The [fast_io](./FASTPOLL.md) version of `uasyncio` in this repo provides a way
to ensure that stream I/O is polled on every iteration of the scheduler. It is
hoped that official `uasyncio` will adopt code to this effect in due course.

###### [Contents](./TUTORIAL.md#contents)

## 6.2 Polling hardware with a coroutine

This is a simple approach, but is most appropriate to hardware which may be
polled at a relatively low rate. This is primarily because polling with a short
(or zero) polling interval may cause the coro to consume more processor time
than is desirable.

The example `apoll.py` demonstrates this approach by polling the Pyboard
accelerometer at 100ms intervals. It performs some simple filtering to ignore
noisy samples and prints a message every two seconds if the board is not moved.

Further examples may be found in `aswitch.py` which provides drivers for
switch and pushbutton devices.

An example of a driver for a device capable of reading and writing is shown
below. For ease of testing Pyboard UART 4 emulates the notional device. The
driver implements a `RecordOrientedUart` class, where data is supplied in
variable length records consisting of bytes instances. The object appends a
delimiter before sending and buffers incoming data until the delimiter is
received. This is a demo and is an inefficient way to use a UART compared to
stream I/O.

For the purpose of demonstrating asynchronous transmission we assume the
device being emulated has a means of checking that transmission is complete
and that the application requires that we wait on this. Neither assumption is
true in this example but the code fakes it with `await asyncio.sleep(0.1)`.

Link pins X1 and X2 to run.

```python
import uasyncio as asyncio
from pyb import UART

class RecordOrientedUart():
    DELIMITER = b'\0'
    def __init__(self):
        self.uart = UART(4, 9600)
        self.data = b''

    def __iter__(self):  # Not __await__ issue #2678
        data = b''
        while not data.endswith(self.DELIMITER):
            yield from asyncio.sleep(0) # Necessary because:
            while not self.uart.any():
                yield from asyncio.sleep(0) # timing may mean this is never called
            data = b''.join((data, self.uart.read(self.uart.any())))
        self.data = data

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

###### [Contents](./TUTORIAL.md#contents)

## 6.3 Using the stream mechanism

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
        print('Received', res)

loop = asyncio.get_event_loop()
loop.create_task(sender())
loop.create_task(receiver())
loop.run_forever()
```

The supporting code may be found in `__init__.py` in the `uasyncio` library.
The mechanism works because the device driver (written in C) implements the
following methods: `ioctl`, `read`, `readline` and `write`. See
[Writing streaming device drivers](./TUTORIAL.md#64-writing-streaming-device-drivers)
for details on how such drivers may be written in Python.

A UART can receive data at any time. The stream I/O mechanism checks for pending
incoming characters whenever the scheduler has control. When a coro is running
an interrupt service routine buffers incoming characters; these will be removed
when the coro yields to the scheduler. Consequently UART applications should be
designed such that coros minimise the time between yielding to the scheduler to
avoid buffer overflows and data loss. This can be ameliorated by using a larger
UART read buffer or a lower baudrate. Alternatively hardware flow control will
provide a solution if the data source supports it.

### 6.3.1 A UART driver example

The program [auart_hd.py](./auart_hd.py) illustrates a method of communicating
with a half duplex device such as one responding to the modem 'AT' command set.
Half duplex means that the device never sends unsolicited data: its
transmissions are always in response to a command from the master.

The device is emulated, enabling the test to be run on a Pyboard with two wire
links.

The (highly simplified) emulated device responds to any command by sending four
lines of data with a pause between each, to simulate slow processing.

The master sends a command, but does not know in advance how many lines of data
will be returned. It starts a retriggerable timer, which is retriggered each
time a line is received. When the timer times out it is assumed that the device
has completed transmission, and a list of received lines is returned.

The case of device failure is also demonstrated. This is done by omitting the
transmission before awaiting a response. After the timeout an empty list is
returned. See the code comments for more details.

###### [Contents](./TUTORIAL.md#contents)

## 6.4 Writing streaming device drivers

The `stream I/O` mechanism is provided to support I/O to stream devices. Its
typical use is to support streaming I/O devices such as UARTs and sockets. The
mechanism may be employed by drivers of any device which needs to be polled:
the polling is delegated to the scheduler which uses `select` to schedule the
handlers for any devices which are ready. This is more efficient than running
multiple coros each polling a device, partly because `select` is written in C
but also because the coroutine performing the polling is descheduled until the
`poll` object returns a ready status.

A device driver capable of employing the stream I/O mechanism may support
`StreamReader`, `StreamWriter` instances or both. A readable device must
provide at least one of the following methods. Note that these are synchronous
methods. The `ioctl` method (see below) ensures that they are only called if
data is available. The methods should return as fast as possible with as much
data as is available.

`readline()` Return as many characters as are available up to and including any
newline character. Required if you intend to use `StreamReader.readline()`  
`read(n)` Return as many characters as are available but no more than `n`.
Required to use `StreamReader.read()` or `StreamReader.readexactly()`  

A writeable driver must provide this synchronous method:  
`write` Args `buf`, `off`, `sz`. Arguments:  
`buf` is the buffer to write.  
`off` is the offset into the buffer of the first character to write.  
`sz` is the requested number of characters to write.  
It should return immediately. The return value is the number of characters
actually written (may well be 1 if the device is slow). The `ioctl` method
ensures that this is only called if the device is ready to accept data.

All devices must provide an `ioctl` method which polls the hardware to
determine its ready status. A typical example for a read/write driver is:

```python
import io
MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL_WR = const(4)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

class MyIO(io.IOBase):
    # Methods omitted
    def ioctl(self, req, arg):  # see ports/stm32/uart.c
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                if hardware_has_at_least_one_char_to_read:
                    ret |= MP_STREAM_POLL_RD
            if arg & MP_STREAM_POLL_WR:
                if hardware_can_accept_at_least_one_write_character:
                    ret |= MP_STREAM_POLL_WR
        return ret
```

The following is a complete awaitable delay class:

```python
import uasyncio as asyncio
import utime
import io
MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

class MillisecTimer(io.IOBase):
    def __init__(self):
        self.end = 0
        self.sreader = asyncio.StreamReader(self)

    def __iter__(self):
        await self.sreader.readline()

    def __call__(self, ms):
        self.end = utime.ticks_add(utime.ticks_ms(), ms)
        return self

    def readline(self):
        return b'\n'

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                if utime.ticks_diff(utime.ticks_ms(), self.end) >= 0:
                    ret |= MP_STREAM_POLL_RD
        return ret
```

which may be used as follows:

```python
async def timer_test(n):
    timer = ms_timer.MillisecTimer()
    await timer(30)  # Pause 30ms
```

With official `uasyncio` this confers no benefit over `await asyncio.sleep_ms()`.
Using [fast_io](./FASTPOLL.md) it offers much more precise delays under the
common usage pattern where coros await a zero delay.

It is possible to use I/O scheduling to associate an event with a callback.
This is more efficient than a polling loop because the coro doing the polling
is descheduled until `ioctl` returns a ready status. The following runs a
callback when a pin changes state.

```python
import uasyncio as asyncio
import io
MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

class PinCall(io.IOBase):
    def __init__(self, pin, *, cb_rise=None, cbr_args=(), cb_fall=None, cbf_args=()):
        self.pin = pin
        self.cb_rise = cb_rise
        self.cbr_args = cbr_args
        self.cb_fall = cb_fall
        self.cbf_args = cbf_args
        self.pinval = pin.value()
        self.sreader = asyncio.StreamReader(self)
        loop = asyncio.get_event_loop()
        loop.create_task(self.run())

    async def run(self):
        while True:
            await self.sreader.read(1)

    def read(self, _):
        v = self.pinval
        if v and self.cb_rise is not None:
            self.cb_rise(*self.cbr_args)
            return b'\n'
        if not v and self.cb_fall is not None:
            self.cb_fall(*self.cbf_args)
        return b'\n'

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                v = self.pin.value()
                if v != self.pinval:
                    self.pinval = v
                    ret = MP_STREAM_POLL_RD
        return ret
```

Once again with official `uasyncio` latency can be high. Depending on
application design the [fast_io](./FASTPOLL.md) version can greatly reduce
this.

The demo program `iorw.py` illustrates a complete example. Note that, at the
time of writing there is a bug in `uasyncio` which prevents this from working.
See [this GitHub thread](https://github.com/micropython/micropython/pull/3836#issuecomment-397317408).
There are two solutions. A workround is to write two separate drivers, one
read-only and the other write-only. Alternatively the
[fast_io](./FASTPOLL.md) version addresses this.

In the official `uasyncio` I/O is scheduled quite infrequently. See 
[see this GitHub RFC](https://github.com/micropython/micropython/issues/2664).
The [fast_io](./FASTPOLL.md) version addresses this issue.

###### [Contents](./TUTORIAL.md#contents)

## 6.5 A complete example: aremote.py

See [aremote.py](./nec_ir/aremote.py) documented [here](./nec_ir/README.md).
The demo provides a complete device driver example: a receiver/decoder for an
infra red remote controller. The following notes are salient points regarding
its `asyncio` usage.

A pin interrupt records the time of a state change (in μs) and sets an event,
passing the time when the first state change occurred. A coro waits on the
event, yields for the duration of a data burst, then decodes the stored data
before calling a user-specified callback.

Passing the time to the `Event` instance enables the coro to compensate for
any `asyncio` latency when setting its delay period.

###### [Contents](./TUTORIAL.md#contents)

## 6.6 HTU21D environment sensor

This chip provides accurate measurements of temperature and humidity. The
driver is documented [here](./htu21d/README.md). It has a continuously running
task which updates `temperature` and `humidity` bound variables which may be
accessed "instantly".

The chip takes on the order of 120ms to acquire both data items. The driver
works asynchronously by triggering the acquisition and using
`await asyncio.sleep(t)` prior to reading the data. This allows other coros to
run while acquisition is in progress.

# 7 Hints and tips

###### [Contents](./TUTORIAL.md#contents)

## 7.1 Program hangs

Hanging usually occurs because a task has blocked without yielding: this will
hang the entire system. When developing it is useful to have a coro which
periodically toggles an onboard LED. This provides confirmation that the
scheduler is running.

###### [Contents](./TUTORIAL.md#contents)

## 7.2 uasyncio retains state

When running programs using `uasyncio` at the REPL, issue a soft reset
(ctrl-D) between runs. This is because `uasyncio` retains state between runs
which can lead to confusing behaviour.

###### [Contents](./TUTORIAL.md#contents)

## 7.3 Garbage Collection

You may want to consider running a coro which issues:

```python
    gc.collect()
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
```

This assumes `import gc` has been issued. The purpose of this is discussed
[here](http://docs.micropython.org/en/latest/pyboard/reference/constrained.html)
in the section on the heap.

###### [Contents](./TUTORIAL.md#contents)

## 7.4 Testing

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

As an example of the type of hazard which can occur, in the `RecordOrientedUart`
example above the `__await__` method was originally written as:

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
because `uart.any()` always returned a nonzero quantity. By the time it was
called, characters had been received. The solution was to yield execution in
the outer loop:

```python
    def __await__(self):
        data = b''
        while not data.endswith(self.DELIMITER):
            yield from asyncio.sleep(0) # Necessary because:
            while not self.uart.any():
                yield from asyncio.sleep(0) # timing may mean this is never called
            data = b''.join((data, self.uart.read(self.uart.any())))
        self.data = data
```

It is perhaps worth noting that this error would not have been apparent had
data been sent to the UART at a slow rate rather than via a loopback test.
Welcome to the joys of realtime programming.

###### [Contents](./TUTORIAL.md#contents)

## 7.5 A common error

If a function or method is defined with `async def` and subsequently called as
if it were a regular (synchronous) callable, MicroPython does not issue an
error message. This is [by design](https://github.com/micropython/micropython/issues/3241).
It typically leads to a program silently failing to run correctly:

```python
async def foo():
    # code
loop.create_task(foo)  # Case 1: foo will never run
foo()  # Case 2: Likewise.
```

I have [a PR](https://github.com/micropython/micropython-lib/pull/292) which
proposes a fix for case 1. The [fast_io](./FASTPOLL.md) version implements
this.

The script [check_async_code.py](./check_async_code.py) attempts to locate
instances of questionable use of coros. It is intended to be run on a PC and
uses Python3. It takes a single argument, a path to a MicroPython sourcefile
(or `--help`). It is designed for use on scripts written according to the
guidelines in this tutorial, with coros declared using `async def`.

Note it is somewhat crude and intended to be used on a syntactically correct
file which is silently failing to run. Use a tool such as `pylint` for general
syntax checking (`pylint` currently misses this error).

The script produces false positives. This is by design: coros are first class
objects; you can pass them to functions and can store them in data structures.
Depending on the program logic you may intend to store the function or the
outcome of its execution. The script can't deduce the intent. It aims to ignore
cases which appear correct while identifying other instances for review.
Assume `foo` is a coro declared with `async def`:

```python
loop.run_until_complete(foo())  # No warning
bar(foo)  # These lines will warn but may or may not be correct
bar(foo())
z = (foo,)
z = (foo(),)
foo()  # Will warn: is surely wrong.
```

I find it useful as-is but improvements are always welcome.

###### [Contents](./TUTORIAL.md#contents)

## 7.6 Socket programming

There are two basic approaches to socket programming under `uasyncio`. By
default sockets block until a specified read or write operation completes.
`uasyncio` supports blocking sockets by using `select.poll` to prevent them
from blocking the scheduler. In most cases it is simplest to use this
mechanism. Example client and server code may be found in the `client_server`
directory. The `userver` application uses `select.poll` explicitly to poll
the server socket. The client sockets use it implicitly in that the `uasyncio`
stream mechanism employs it.

Note that `socket.getaddrinfo` currently blocks. The time will be minimal in
the example code but if a DNS lookup is required the blocking period could be
substantial.

The second approach to socket programming is to use nonblocking sockets. This
adds complexity but is necessary in some applications, notably where
connectivity is via WiFi (see below).

At the time of writing (March 2019) support for TLS on nonblocking sockets is
under development. Its exact status is unknown (to me).

The use of nonblocking sockets requires some attention to detail. If a
nonblocking read is performed, because of server latency, there is no guarantee
that all (or any) of the requested data is returned. Likewise writes may not
proceed to completion.

Hence asynchronous read and write methods need to iteratively perform the
nonblocking operation until the required data has been read or written. In
practice a timeout is likely to be required to cope with server outages.

A further complication is that the ESP32 port had issues which required rather
unpleasant hacks for error-free operation. I have not tested whether this is
still the case.

The file [sock_nonblock.py](./sock_nonblock.py) illustrates the sort of
techniques required. It is not a working demo, and solutions are likely to be
application dependent.

### 7.6.1 WiFi issues

The `uasyncio` stream mechanism is not good at detecting WiFi outages. I have
found it necessary to use nonblocking sockets to achieve resilient operation
and client reconnection in the presence of outages.

[This doc](https://github.com/peterhinch/micropython-samples/blob/master/resilient/README.md)
describes issues I encountered in WiFi applications which keep sockets open for
long periods, and outlines a solution.

[This repo](https://github.com/peterhinch/micropython-mqtt.git) offers a
resilent asynchronous MQTT client which ensures message integrity over WiFi
outages. [This repo](https://github.com/peterhinch/micropython-iot.git)
provides a simple asynchronous full-duplex serial channel between a wirelessly
connected client and a wired server with guaranteed message delivery.

###### [Contents](./TUTORIAL.md#contents)

## 7.7 Event loop constructor args

A subtle bug can arise if you need to instantiate the event loop with non
default values. Instantiation should be performed before running any other
`asyncio` code. This is because the code may acquire the event loop. In
doing so it initialises it to the default values:

```python
import uasyncio as asyncio
import some_module
bar = some_module.Bar()  # Constructor calls get_event_loop()
# and renders these args inoperative
loop = asyncio.get_event_loop(runq_len=40, waitq_len=40)
```

Given that importing a module can run code the safest way is to instantiate
the event loop immediately after importing `uasyncio`.

```python
import uasyncio as asyncio
loop = asyncio.get_event_loop(runq_len=40, waitq_len=40)
import some_module
bar = some_module.Bar()  # The get_event_loop() call is now safe
```

My preferred approach to this is as follows. If writing modules for use by
other programs avoid running `uasyncio` code on import. Write functions and
methods to expect the event loop as an arg. Then ensure that only the top level
application calls `get_event_loop`:

```python
import uasyncio as asyncio
import my_module  # Does not run code on loading
loop = asyncio.get_event_loop(runq_len=40, waitq_len=40)
bar = my_module.Bar(loop)
```

Ref [this issue](https://github.com/micropython/micropython-lib/issues/295).

###### [Contents](./TUTORIAL.md#contents)

# 8 Notes for beginners

These notes are intended for those new to asynchronous code. They start by
outlining the problems which schedulers seek to solve, and give an overview of
the `uasyncio` approach to a solution.

[Section 8.5](./TUTORIAL.md#85-why-cooperative-rather-than-pre-emptive)
discusses the relative merits of `uasyncio` and the `_thread` module and why
you may prefer use cooperative (`uasyncio`) over pre-emptive (`_thread`)
scheduling.

###### [Contents](./TUTORIAL.md#contents)

## 8.1 Problem 1: event loops

A typical firmware application runs continuously and is required to respond to
external events. These might include a voltage change on an ADC, the arrival of
a hard interrupt, a character arriving on a UART, or data being available on a
socket. These events occur asynchronously and the code must be able to respond
regardless of the order in which they occur. Further the application may be
required to perform time-dependent tasks such as flashing LED's.

The obvious way to do this is with an event loop. The following is not
practical code but serves to illustrate the general form of an event loop.

```python
def event_loop():
    led_1_time = 0
    led_2_time = 0
    switch_state = switch.state()  # Current state of a switch
    while True:
        time_now = utime.time()
        if time_now >= led_1_time:  # Flash LED #1
            led1.toggle()
            led_1_time = time_now + led_1_period
        if time_now >= led_2_time:  # Flash LED #2
            led2.toggle()
            led_2_time = time_now + led_2_period
        # Handle LEDs 3 upwards

        if switch.value() != switch_state:
            switch_state = switch.value()
            # do something
        if uart.any():
            # handle UART input
```

This works for simple examples but event loops rapidly become unwieldy as the
number of events increases. They also violate the principles of object oriented
programming by lumping much of the program logic in one place rather than
associating code with the object being controlled. We want to design a class
for an LED capable of flashing which could be put in a module and imported. An
OOP approach to flashing an LED might look like this:

```python
import pyb
class LED_flashable():
    def __init__(self, led_no):
        self.led = pyb.LED(led_no)

    def flash(self, period):
        while True:
            self.led.toggle()
            # somehow wait for period but allow other
            # things to happen at the same time
```

A cooperative scheduler such as `uasyncio` enables classes such as this to be
created.

###### [Contents](./TUTORIAL.md#contents)

## 8.2 Problem 2: blocking methods

Assume you need to read a number of bytes from a socket. If you call
`socket.read(n)` with a default blocking socket it will "block" (i.e. fail to
return) until `n` bytes have been received. During this period the application
will be unresponsive to other events.

With `uasyncio` and a non-blocking socket you can write an asynchronous read
method. The task requiring the data will (necessarily) block until it is
received but during that period other tasks will be scheduled enabling the
application to remain responsive.

## 8.3 The uasyncio approach

The following class provides for an LED which can be turned on and off, and
which can also be made to flash at an arbitrary rate. A `LED_async` instance
has a `run` method which can be considered to run continuously. The LED's
behaviour can be controlled by methods `on()`, `off()` and `flash(secs)`.

```python
import pyb
import uasyncio as asyncio

class LED_async():
    def __init__(self, led_no):
        self.led = pyb.LED(led_no)
        self.rate = 0
        loop = asyncio.get_event_loop()
        loop.create_task(self.run())

    async def run(self):
        while True:
            if self.rate <= 0:
                await asyncio.sleep_ms(200)
            else:
                self.led.toggle()
                await asyncio.sleep_ms(int(500 / self.rate))

    def flash(self, rate):
        self.rate = rate

    def on(self):
        self.led.on()
        self.rate = 0

    def off(self):
        self.led.off()
        self.rate = 0
```

Note that `on()`, `off()` and `flash()` are conventional synchronous methods.
They change the behaviour of the LED but return immediately. The flashing
occurs "in the background". This is explained in detail in the next section.

The class conforms with the OOP principle of keeping the logic associated with
the device within the class. Further, the way `uasyncio` works ensures that
while the LED is flashing the application can respond to other events. The
example below flashes the four Pyboard LED's at different rates while also
responding to the USR button which terminates the program.

```python
import pyb
import uasyncio as asyncio
from led_async import LED_async  # Class as listed above

async def killer():
    sw = pyb.Switch()
    while not sw.value():
        await asyncio.sleep_ms(100)

leds = [LED_async(n) for n in range(1, 4)]
for n, led in enumerate(leds):
    led.flash(0.7 + n/4)
loop = asyncio.get_event_loop()
loop.run_until_complete(killer())
```

In contrast to the event loop example the logic associated with the switch is
in a function separate from the LED functionality. Note the code used to start
the scheduler:

```python
loop = asyncio.get_event_loop()
loop.run_until_complete(killer())  # Execution passes to coroutines.
 # It only continues here once killer() terminates, when the
 # scheduler has stopped.
```

###### [Contents](./TUTORIAL.md#contents)

## 8.4 Scheduling in uasyncio

Python 3.5 and MicroPython support the notion of an asynchronous function,
also known as a coroutine (coro) or task. A coro must include at least one
`await` statement.

```python
async def hello():
    for _ in range(10):
        print('Hello world.')
        await asyncio.sleep(1)
```

This function prints the message ten times at one second intervals. While the
function is paused pending the time delay asyncio will schedule other tasks,
providing an illusion of concurrency.

When a coro issues `await asyncio.sleep_ms()` or `await asyncio.sleep()` the
current task pauses: it is placed on a queue which is ordered on time due, and
execution passes to the task at the top of the queue. The queue is designed so
that even if the specified sleep is zero other due tasks will run before the
current one is resumed. This is "fair round-robin" scheduling. It is common
practice to issue `await asyncio.sleep(0)` in loops to ensure a task doesn't
hog execution. The following shows a busy-wait loop which waits for another
task to set the global `flag`. Alas it monopolises the CPU preventing other
coros from running:

```python
async def bad_code():
    global flag
    while not flag:
        pass
    flag = False
    # code omitted
```

The problem here is that while the `flag` is `False` the loop never yields to
the scheduler so no other task will get to run. The correct approach is:

```python
async def good_code():
    global flag
    while not flag:
        await asyncio.sleep(0)
    flag = False
    # code omitted
```

For the same reason it's bad practice to issue delays like `utime.sleep(1)`
because that will lock out other tasks for 1s; use `await asyncio.sleep(1)`.
Note that the delays implied by `uasyncio` methods `sleep` and  `sleep_ms` can
overrun the specified time. This is because while the delay is in progress
other tasks will run. When the delay period completes, execution will not
resume until the running task issues `await` or terminates. A well-behaved coro
will always issue `await` at regular intervals. Where a precise delay is
required, especially one below a few ms, it may be necessary to use
`utime.sleep_us(us)`.

###### [Contents](./TUTORIAL.md#contents)

## 8.5 Why cooperative rather than pre-emptive?

The initial reaction of beginners to the idea of cooperative multi-tasking is
often one of disappointment. Surely pre-emptive is better? Why should I have to
explicitly yield control when the Python virtual machine can do it for me?

When it comes to embedded systems the cooperative model has two advantages.
Firstly, it is lightweight. It is possible to have large numbers of coroutines
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
a coro and periodically issuing `await asyncio.sleep(0)`.

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
complete control until it issues `await asyncio.sleep(0)`.

Bear in mind that interrupt handlers are pre-emptive. This applies to both hard
and soft interrupts, either of which can occur at any point in your code.

An eloquent discussion of the evils of threading may be found
[in threads are bad](https://glyph.twistedmatrix.com/2014/02/unyielding.html).

###### [Contents](./TUTORIAL.md#contents)

## 8.6 Communication

In non-trivial applications coroutines need to communicate. Conventional Python
techniques can be employed. These include the use of global variables or
declaring coros as object methods: these can then share instance variables.
Alternatively a mutable object may be passed as a coro argument.

Pre-emptive systems mandate specialist classes to achieve "thread safe"
communications; in a cooperative system these are seldom required.

###### [Contents](./TUTORIAL.md#contents)

## 8.7 Polling

Some hardware devices such as the Pyboard accelerometer don't support
interrupts, and therefore must be polled (i.e. checked periodically). Polling
can also be used in conjunction with interrupt handlers: the interrupt handler
services the hardware and sets a flag. A coro polls the flag: if it's set it
handles the data and clears the flag. A better approach is to use an `Event`.

###### [Contents](./TUTORIAL.md#contents)
