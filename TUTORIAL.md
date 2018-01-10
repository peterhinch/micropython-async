# Application of uasyncio to hardware interfaces

This document is a "work in progress" as uasyncio is itself under development.
Please report any errors you discover.

The MicroPython uasyncio library comprises a subset of Python's asyncio library
designed for use on microcontrollers. As such it has a small RAM footprint and
fast context switching with zero RAM allocation. This document describes its
use with a focus on interfacing hardware devices. The aim is to design drivers
in such a way that the application continues to run while the driver is waiting
for a response from the hardware or for a user interaction.

Another major application area for asyncio is in network programming: many
guides to this may be found online.

Note that MicroPython is based on Python 3.4 with minimal Python 3.5 additions.
Except where detailed below, `asyncio` features of versions >3.4 are
unsupported. As stated above it is a subset. This document identifies supported
features.

# Installing uasyncio on bare metal

MicroPython libraries are located on [PyPi](https://pypi.python.org/pypi).
Libraries to be installed are:

 * micropython-uasyncio
 * micropython-uasyncio.queues
 * micropython-uasyncio.synchro

The `queues` and `synchro` modules are optional, but are required to run all
the examples below.

The oficial approach is to use the `upip` utility as described
[here](https://github.com/micropython/micropython-lib). Network enabled
hardware has this included in the firmware so it can be run locally. This is
the preferred approach.

On non-networked hardware there are two options. One is to use `upip` under a
Linux real or virtual machine. This involves installing and building the Unix
version of MicroPython, using `upip` to install to a directory on the PC, and
then copying the library to the target.

The need for Linux and the Unix build may be avoided by using
[micropip.py](https://github.com/peterhinch/micropython-samples/tree/master/micropip).
This runs under Python 3.2 or above. Create a temporary directory on your PC
and install to that. Then copy the contents of the temporary direcory to the
device. The following assume Linux and a temporary directory named `~/syn` -
adapt to suit your OS. The first option requires that `micropip.py` has
executable permission.

```
$ ./micropip.py install -p ~/syn micropython-uasyncio
$ python3 -m micropip.py install -p ~/syn micropython-uasyncio
```

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

   3.1.1 [Locks and timeouts](./TUTORIAL.md#311-locks-and-timeouts)

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

  4.5 [Exceptions](./TUTORIAL.md#45-exceptions)

 5. [Device driver examples](./TUTORIAL.md#5-device-driver-examples)

  5.1 [The IORead mechnaism](./TUTORIAL.md#51-the-ioread-mechanism)

  5.2 [Using a coro to poll hardware](./TUTORIAL.md#52-using-a-coro-to-poll-hardware)

  5.3 [Using IORead to poll hardware](./TUTORIAL.md#53-using-ioread-to-poll-hardware)

  5.4 [A complete example: aremote.py](./TUTORIAL.md#54-a-complete-example-aremotepy)

 6. [Hints and tips](./TUTORIAL.md#6-hints-and-tips)

  6.1 [Coroutines are generators](./TUTORIAL.md#61-coroutines-are-generators)

  6.2 [Program hangs](./TUTORIAL.md#62-program-hangs)

  6.3 [uasyncio retains state](./TUTORIAL.md#63-uasyncio-retains-state)

  6.4 [Garbage Collection](./TUTORIAL.md#64-garbage-collection)

  6.5 [Testing](./TUTORIAL.md#65-testing)

  6.6 [A common hard to find error](./TUTORIAL.md#66-a-common-error)

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

###### [Contents](./TUTORIAL.md#contents)

## 1.1 Modules

The following modules are provided which may be copied to the target hardware.

**Libraries**

 1. `asyn.py` Provides synchronisation primitives `Lock`, `Event`, `Barrier`,
 `Semaphore` and `BoundedSemaphore`. Provides support for task cancellation via
 `NamedTask` and `Cancellable` classes.
 2. `aswitch.py` This provides classes for interfacing switches and
 pushbuttons and also a software retriggerable delay object. Pushbuttons are a
 generalisation of switches providing logical rather than physical status along
 with double-clicked and long pressed events.
 3. `asyncio_priority.py` An experimental version of uasyncio with a simple
 priority mechanism. See [this doc](./FASTPOLL.md).

**Demo Programs**

The first two are the most immediately rewarding as they produce visible
results by accessing Pyboard hardware.

 1. `aledflash.py` Flashes the four Pyboard LED's asynchronously for 10s. The
 simplest uasyncio demo. Import it to run.
 2. `apoll.py` A device driver for the Pyboard accelerometer. Demonstrates
 the use of a coroutine to poll a device. Runs for 20s. Import it to run.
 3. `astests.py` Test/demonstration programs for the `aswitch` module.
 4. `asyn_demos.py` Simple task cancellation demos.
 5. `roundrobin.py` Demo of round-robin scheduling. Also a benchmark of
 scheduling performance.
 6. `awaitable.py` Demo of an awaitable class. One way of implementing a
 device driver which polls an interface.
 7. `chain.py` Copied from the Python docs. Demo of chaining coroutines.
 8. `aqtest.py` Demo of uasyncio `Queue` class.
 9. `aremote.py` Example device driver for NEC protocol IR remote control.
 10. `auart.py` Demo of streaming I/O via a Pyboard UART.

**Test Programs**

 1. `asyntest.py` Tests for the synchronisation primitives in `asyn.py`.
 2. `cantest.py` Task cancellation tests.

**Utility**

 1. `check_async_code.py` A Python3 utility to locate a particular coding
 error which can be hard to find. See [this para](./TUTORIAL.md#65-a-common-error).

**Benchmarks**

The `benchmarks` directory contains scripts to test and characterise the
uasyncio scheduler. See [this doc](./FASTPOLL.md).

###### [Contents](./TUTORIAL.md#contents)

# 2. uasyncio

The asyncio concept is of cooperative multi-tasking based on coroutines,
referred in this document as coros or tasks.

###### [Contents](./TUTORIAL.md#contents)

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

Program execution proceeds normally until the call to `loop.run_forever`. At
this point execution is controlled by the scheduler. A line after
`loop.run_forever` would never be executed. The scheduler runs `bar`
because this has been placed on the scheduler's queue by `loop.create_task`.
In this trivial example there is only one coro: `bar`. If there were others,
the scheduler would schedule them in periods when `bar` was paused.

Many embedded applications have an event loop which runs continuously. The event
loop can also be started in a way which permits termination, by using the event
loop's `run_until_complete` method. Examples of this may be found in the
`astests.py` module.

The event loop instance is a singleton, instantiated by a program's first call
to `asyncio.get_event_loop()`. This takes an optional integer arg being the
length of the coro queue - i.e. the maximum number of concurrent coros allowed.
The default of 42 is likely to be adequate for most purposes. If a coro needs
to call an event loop method, calling `asyncio.get_event_loop()` (without
args) will efficiently return it.

###### [Contents](./TUTORIAL.md#contents)

## 2.2 Coroutines (coros)

A coro is instantiated as follows:

```python
async def foo(delay_secs):
    await asyncio.sleep(delay_secs)
    print('Hello')
```

A coro can allow other coroutines to run by means of the `await coro`
statement. A coro must contain at least one `await` statement. This causes
`coro` to run to completion before execution passes to the next instruction.
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
 the coro ASAP and blocks until it has run to completion.

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
this is discussed further in [Section 5](./TUTORIAL.md#5-device-driver-examples).

Very precise delays may be issued by using the `utime` functions `sleep_ms`
and `sleep_us`. These are best suited for short delays as the scheduler will
be unable to schedule other coros while the delay is in progress.

###### [Contents](./TUTORIAL.md#contents)

# 3 Synchronisation

There is often a need to provide synchronisation between coros. A common
example is to avoid what are known as "race conditions" where multiple coros
compete to access a single resource. An example is provided in the `astests.py`
program and discussed in [the docs](./DRIVERS.md). Another hazard is the "deadly
embrace" where two coros each wait on the other's completion.

In simple applications communication may be achieved with global flags. A more
elegant approach is to use synchronisation primitives. The module `asyn.py`
offers "micro" implementations of `Event`, `Barrier` and `Semaphore`
primitives. These are for use only with asyncio. They are not thread safe and
should not be used with the `_thread` module. A `Lock` primitive is provided
but is now largely superseded by an official implementation.

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

This describes the use of the official `Lock` primitive. [Full details.](./PRIMITIVES.md#32-class-lock)

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
If a coro is subject to a [timeout](./TUTORIAL.md#44-coroutines-with-timeouts)
and the timeout is triggered while it is waiting on a lock, the timeout will be
ineffective. It will not receive the `TimeoutError` until it has acquired the
lock. The same observation applies to task cancellation.

The module `asyn.py` offers a `Lock` class which works in these situations. It
is significantly less efficient than the official class.

###### [Contents](./TUTORIAL.md#contents)

## 3.2 Event

This provides a way for one or more coros to pause until another flags them to
continue. An `Event` object is instantiated and made accessible to all coros
using it. Coros waiting on the event issue `await event` whereupon execution
pauses until another issues `event.set()`. [Full details.](./PRIMITIVES.md#33-class-event)

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

Where multiple coros wait on a single event synchronisationcan be achieved by
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
is for the coro setting the event to issue `event.set(loop.time())`. Any coro
waiting on the event can determine the latency incurred, for example to perform
compensation for this.

###### [Contents](./TUTORIAL.md#contents)

## 3.3 Barrier

This enables multiple coros to rendezvous at a particular point. For example
producer and consumer coros can synchronise at a point where the producer has
data available and the consumer is ready to use it. At that point in time the
`Barrier` can optionally run a callback before releasing the barrier and
allowing all waiting coros to continue. [Full details.](./PRIMITIVES.md#34-class-barrier)

The callback can be a function or a coro. In most applications a function is
likely to be used: this can be guaranteed to run to completion before the
barrier is released.

An example is the `barrier_test` function in `asyntest.py`. In the code
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

## 3.6 Task cancellation

This requires `uasyncio` V1.7.1 which was released on 7th Jan 2018, with
firmware of that date or later.

`uasyncio` now provides a `cancel(coro)` function. This works by throwing an
exception to the coro in a special way: cancellation is deferred until the coro
is next scheduled. This mechanism works with nested coros. However there is a
limitation. If a coro issues `await uasyncio.sleep(secs)` or
`uasyncio.sleep_ms(ms)` scheduling will not occur until the time has elapsed.
This introduces latency into cancellation which matters in some use-cases.
Other potential sources of latency take the form of slow code. `uasyncio` has
no mechanism for verifying when cancellation has actually occurred. The `asyn`
library provides solutions via the following classes:

 1. `Cancellable` This allows one or more tasks to be assigned to a group. A
 coro can cancel all tasks in the group, pausing until this has been acheived.
 Documentation may be found [here](./PRIMITIVES.md#42-class-cancellable).
 2. `NamedTask` This enables a coro to be associated with a user-defined name.
 The running status of named coros may be checked. For advanced usage more
 complex groupings of tasks can be created. Documentation may be found
 [here](./PRIMITIVES.md#43-class-namedtask).

A typical use-case is as follows:

```python
async def comms():  # Perform some communications task
    while True:
        await initialise_link()
        try:
            await do_communications()  # Launches Cancellable tasks
        except CommsError:
            await Cancellable.cancel_all()
        # All sub-tasks are now known to be stopped. They can be re-started
        # with known initial state on next pass.
```

Examples of the usage of these classes may be found in `asyn_demos.py`. For an
illustration of the mechanism a cancellable task is defined as below:

```python
@asyn.cancellable
async def print_nums(_, num):
    while True:
        print(num)
        num += 1
        await asyn.sleep(1)
```

It is launched and cancelled with:

```python
async def foo():
    loop = asyncio.get_event_loop()
    loop.create_task(asyn.Cancellable(print_nums, 42)())
    await asyn.sleep(7.5)
    await asyn.Cancellable.cancel_all()
    print('Done')
```

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

    __iter__ = __await__  # See note below

async def bar():
    foo = Foo()  # Foo is an awaitable class
    print('waiting for foo')
    await foo
    print('done')

loop = asyncio.get_event_loop()
loop.run_until_complete(bar())
```

Currently MicroPython doesn't support `__await__` (issue #2678) and
`__iter__` must be used. The line `__iter__ = __await__` enables portability
between CPython and MicroPython.

Example code may be found in the `Event` and `Barrier` classes in asyn.py.

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
defined, both being coros waiting on an `awaitable` object. This example comes
from the `Lock` class:

```python
    async def __aenter__(self):
        await self.acquire()  # a coro defined with async def

    async def __aexit__(self, *args):
        self.release()  # A conventional method
        await asyncio.sleep_ms(0)
```

Note there is currently a bug in the implementation whereby if an explicit
`return` is issued within an `async with` block, the `__aexit__` method
is not called. The solution is to design the code so that in all cases it runs
to completion. The error appears to be in [PEP492](https://www.python.org/dev/peps/pep-0492/).
See [this issue](https://github.com/micropython/micropython/issues/3153).

###### [Contents](./TUTORIAL.md#contents)

## 4.4 Coroutines with timeouts

This requires uasyncio.core V1.7 which was released on 16th Dec 2017, with
firmware of that date or later.

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

If this matters to the application, create a long delay by awaiting a short one
in a loop. The coro `asyn.sleep` [supports this](./PRIMITIVES.md#41-coro-sleep).

## 4.5 Exceptions

Where an exception occurs in a coro, it should be trapped either in that coro
or in a coro which is awaiting its completion. This ensures that the exception
is not propagated to the scheduler. If this occurred it would stop running,
passing the exception to the code which started the scheduler.

Using `throw` to throw an exception to a coro is unwise. It subverts the design
of `uasyncio` by forcing the coro to run, and possibly terminate, when it is
still queued for execution. I haven't entirely thought through the implications
of this, but it's a thoroughly bad idea.

###### [Contents](./TUTORIAL.md#contents)

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
done using a hardware timer with a hard interrupt callback. For "very"
repeatable read microsecond level (depending on platform).

In many cases less precise timing is acceptable. The definition of "less" is
application dependent but the latency associated with scheduling the coro which
is performing the polling may be variable on the order of tens or hundreds of
milliseconds. Latency is determined as follows. When `await asyncio.sleep(0)`
is issued all other pending coros will be scheduled in "fair round-robin"
fashion before it is re-scheduled. Thus its worst-case latency may be
calculated by summing, for every other coro, the worst-case execution time
between yielding to the scheduler.

If `await asyncio.sleep_ms(t)` is issued where t > 0 the coro is guaranteed not
to be rescheduled until t has elapsed. If, at that time, all other coros are
waiting on nonzero delays, it will immediately be scheduled. But if other coros
are pending execution (either because they issued a zero delay or because their
time has elapsed) they may be scheduled first. This introduces a timing
uncertainty into the `sleep()` and `sleep_ms()` functions. The worst-case value
for this may be calculated as above.

[This document](./FASTPOLL.md) describes an experimental version of uasyncio
which offers a means of reducing this latency for critical tasks.

###### [Contents](./TUTORIAL.md#contents)

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

The supporting code may be found in `__init__.py` in the uasyncio library.
The mechanism works because the device driver (written in C) implements the
following methods: `ioctl`, `read`, `write`, `readline` and `close`. See
section 5.3 for further discussion.

###### [Contents](./TUTORIAL.md#contents)

## 5.2 Using a coro to poll hardware

This is a simple approach, but is only appropriate to hardware which is to be
polled at a relatively low rate. This is for two reasons. Firstly the variable
latency caused by the execution of other coros will result in variable polling
intervals - this may or may not matter depending on the device and application.
Secondly, attempting to poll with a short polling interval may cause the coro
to consume more processor time than is desirable.

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
IORead.

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

###### [Contents](./TUTORIAL.md#contents)

## 5.3 Using IORead to poll hardware

The uasyncio `IORead` class is provided to support IO to stream devices. It
may be employed by drivers of devices which need to be polled: the polling will
be delegated to the scheduler which uses `select` to schedule the first
stream or device driver to be ready. This is more efficient, and offers lower
latency, than running multiple coros each polling a device.

At the time of writing firmware support for using this mechanism in device
drivers written in Python has not been implemented, and the final comment to
[this](https://github.com/micropython/micropython/issues/2664) issue suggests
that it may never be done. So streaming device drivers must be written in C.

###### [Contents](./TUTORIAL.md#contents)

## 5.4 A complete example: aremote.py

This may be found in the `nec_ir` directory. Its use is documented
[here](./nec_ir/README.md). The demo provides a complete device driver example:
a receiver/decoder for an infra red remote controller. The following notes are
salient points regarding its asyncio usage.

A pin interrupt records the time of a state change (in us) and sets an event,
passing the time when the first state change occurred. A coro waits on the
event, yields for the duration of a data burst, then decodes the stored data
before calling a user-specified callback.

Passing the time to the `Event` instance enables the coro to compensate for
any asyncio latency when setting its delay period.

###### [Contents](./TUTORIAL.md#contents)

# 6 Hints and tips

## 6.1 Coroutines are generators

In MicroPython coroutines are generators. This is not the case in CPython.
Issuing `yield` in a coro will provoke a syntax error in CPython, whereas in
MicroPython it has the same effect as `await asyncio.sleep(0)`. The surest way
to write error free code is to use CPython conventions and assume that coros
are not generators.

The following will work. If you use them, be prepared to test your code against
each uasyncio release because the behaviour is not necessarily guaranteed.

```python
yield from coro  # Equivalent to await coro: continue when coro terminates.
yield  # Reschedule current coro in round-robin fashion.
yield 100  # Pause 100ms - equivalent to above
```

Issuing `yield` or `yield 100` is slightly faster than the equivalent `await`
statements.

###### [Contents](./TUTORIAL.md#contents)

## 6.1 Program hangs

Hanging usually occurs because a task has blocked without yielding: this will
hang the entire system. When developing it is useful to have a coro which
periodically toggles an onboard LED. This provides confirmtion that the
scheduler is running.

###### [Contents](./TUTORIAL.md#contents)

## 6.2 uasyncio retains state

When running programs using `uasyncio` at the REPL, issue a soft reset
(ctrl-D) between runs. This is because `uasyncio` retains state between runs
which can lead to confusing behaviour.

###### [Contents](./TUTORIAL.md#contents)

## 6.3 Garbage Collection

You may want to consider running a coro which issues:

```python
    gc.collect()
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
```

This assumes `import gc` has been issued. The purpose of this is discussed
[here](http://docs.micropython.org/en/latest/pyboard/reference/constrained.html)
in the section on the heap.

###### [Contents](./TUTORIAL.md#contents)

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
            yield from asyncio.sleep(0) # Neccessary because:
            while not self.uart.any():
                yield from asyncio.sleep(0) # timing may mean this is never called
            data = b''.join((data, self.uart.read(self.uart.any())))
        self.data = data
```

It is perhaps worth noting that this error would not have been apparent had
data been sent to the UART at a slow rate rather than via a loopback test.

###### [Contents](./TUTORIAL.md#contents)

## 6.5 A common error

If a function or method is defined with `async def` and subsequently called as
if it were a regular (synchronous) callable, MicroPython does not issue an
error message. This is [by design](https://github.com/micropython/micropython/issues/3241).
It typically leads to a program silently failing to run correctly.

The script `check_async_code.py` attempts to locate instances of questionable
use of coros. It is intended to be run on a PC and uses Python3. It takes a
single argument, a path to a MicroPython sourcefile (or `--help`). It is
designed for use on scripts written according to the guidelines in this
tutorial, with coros declared using `async def`.

Note it is somewhat crude and intended to be used on a syntactically correct
file which is silently failing to run. Use a tool such as pylint for general
syntax checking (pylint currently misses this error).

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
```

I find it useful as-is but improvements are always welcome.

###### [Contents](./TUTORIAL.md#contents)

# 7 Notes for beginners

These notes are intended for those unfamiliar with asynchronous code or unsure
of the relative merits of asyncio and the _thread module (i.e. cooperative vs
pre-emptive scheduling).

###### [Contents](./TUTORIAL.md#contents)

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
will get positively convoluted. Using asyncio with the `aswitch.py` module we
can write:

```python
async def cb(button_no):  # user code omitted. This runs when
                    # button pressed, with the button number passed

buttons = ('X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8', 'X9', 'X10', 'X11', 'X12')
for button_no, button in enumerate(buttons):
    pb = Pushbutton(Pin(button, Pin.IN, Pin.PULL_UP)
    pb.press_coro(cb, (button_no,))
```

The `Pushbutton` class hides the detail, but for each button a coroutine is
created which polls the `Pin` object and performs the debouncing. It can also
start user supplied coroutines on button release events, long presses and
double clicks. The code in `aswitch.py` achieves this using asyncio.

Scheduling also solves the problem of blocking. If a routine needs to wait for
a physical event to occur before it can continue it is said to be blocked. You
may not want the entire system to be blocked. While this can be solved in
linear code, in threaded code the solution is trivial. The coroutine blocks,
but while it does so it periodically yields execution. Hence the rest of the
system continues to run.

###### [Contents](./TUTORIAL.md#contents)

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

An eloquent discussion of the merits of cooperative multi-tasking may be found
[in threads are bad](https://glyph.twistedmatrix.com/2014/02/unyielding.html).

###### [Contents](./TUTORIAL.md#contents)

## 7.3 Communication

In non-trivial applications coroutines need to communicate. Conventional Python
techniques can be employed. These include the use of global variables or
declaring coros as object methods: these can then share instance variables.
Alternatively a mutable object may be passed as a coro argument.

Pre-emptive systems mandate specialist classes to achieve "thread safe"
communications; in a cooperative system these are seldom required.

###### [Contents](./TUTORIAL.md#contents)

## 7.4 Polling

Some hardware devices such as the Pyboard accelerometer don't support
interrupts, and therefore must be polled (i.e. checked periodically). Polling
can also be used in conjunction with interrupt handlers: the interrupt handler
services the hardware and sets a flag. A coro polls the flag: if it's set it
handles the data and clears the flag.

###### [Contents](./TUTORIAL.md#contents)

# 8 Modifying uasyncio

The library is designed to be extensible, an example being the
`asyncio_priority` module. By following the following guidelines a module can
be constructed which alters the functionality of asyncio without the need to
change the official library. Such a module may be used where `uasyncio` is
implemented as frozen bytecode.

Assume that the aim is to alter the event loop. The module should issue

```python
from uasyncio import *
```

The event loop should be subclassed from `PollEventLoop` (defined in
`__init__.py`).

The event loop is instantiated by the first call to `get_event_loop()`: this
creates a singleton instance. This is returned by every call to
`get_event_loop()`. On the assumption that the constructor arguments for the
new class differ from those of the base class, the module will need to redefine
`get_event_loop()` along the following lines:

```python
_event_loop = None  # The singleton instance
_event_loop_class = MyNewEventLoopClass  # The class, not an instance
def get_event_loop(args):
    global _event_loop
    if _event_loop is None:
        _event_loop = _event_loop_class(args)  # Instantiate once only
    return _event_loop
```
