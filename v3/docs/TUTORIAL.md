# Application of uasyncio to hardware interfaces

This tutorial is intended for users having varying levels of experience with
asyncio and includes a section for complete beginners. It is based on the
current version of `uasyncio`, V3.0.0. Most code samples are complete scripts
which can be cut and pasted at the REPL.

See [this overview](../README.md) for a summary of resources for `uasyncio`
including device drivers, debugging aids, and documentation.

# Contents

 0. [Introduction](./TUTORIAL.md#0-introduction)  
  0.1 [Installing uasyncio](./TUTORIAL.md#01-installing-uasyncio)  
 1. [Cooperative scheduling](./TUTORIAL.md#1-cooperative-scheduling)  
  1.1 [Modules](./TUTORIAL.md#11-modules)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.1 [Primitives](./TUTORIAL.md#111-primitives)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.2 [Demo programs](./TUTORIAL.md#112-demo-programs)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1.1.3 [Device drivers](./TUTORIAL.md#113-device-drivers)  
 2. [uasyncio](./TUTORIAL.md#2-uasyncio)  
  2.1 [Program structure](./TUTORIAL.md#21-program-structure)  
  2.2 [Coroutines and Tasks](./TUTORIAL.md#22-coroutines-and-tasks)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.2.1 [Queueing a task for scheduling](./TUTORIAL.md#221-queueing-a-task-for-scheduling)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.2.2 [Running a callback function](./TUTORIAL.md#222-running-a-callback-function)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.2.3 [Notes](./TUTORIAL.md#223-notes) Coros as bound methods. Returning values.  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.2.4 [A typical firmware app](./TUTORIAL.md#224-a-typical-firmware-app) Avoiding a minor error  
  2.3 [Delays](./TUTORIAL.md#23-delays)  
 3. [Synchronisation](./TUTORIAL.md#3-synchronisation)  
  3.1 [Lock](./TUTORIAL.md#31-lock)  
  3.2 [Event](./TUTORIAL.md#32-event)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.2.1 [Wait on multiple events](./TUTORIAL.md#321-wait-on-multiple-events) Pause until 1 of N events is set.  
  3.3 [Coordinating multiple tasks](./TUTORIAL.md#33-coordinating-multiple-tasks)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.3.1 [gather](./TUTORIAL.md#331-gather)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.3.2 [TaskGroups](./TUTORIAL.md#332-taskgroups) Not yet in official build.  
  3.4 [Semaphore](./TUTORIAL.md#34-semaphore)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.4.1 [BoundedSemaphore](./TUTORIAL.md#341-boundedsemaphore)  
  3.5 [Queue](./TUTORIAL.md#35-queue)  
  3.6 [ThreadSafeFlag](./TUTORIAL.md#36-threadsafeflag) Synchronisation with asynchronous events and interrupts.  
  3.7 [Barrier](./TUTORIAL.md#37-barrier)  
  3.8 [Delay_ms](./TUTORIAL.md#38-delay_ms-class) Software retriggerable delay.  
  3.9 [Message](./TUTORIAL.md#39-message)  
  3.10 [Synchronising to hardware](./TUTORIAL.md#310-synchronising-to-hardware)
  Debouncing switches, pushbuttons, ESP32 touchpads and encoder knobs. Taming ADC's.  
 4. [Designing classes for asyncio](./TUTORIAL.md#4-designing-classes-for-asyncio)  
  4.1 [Awaitable classes](./TUTORIAL.md#41-awaitable-classes)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.1.1 [Use in context managers](./TUTORIAL.md#411-use-in-context-managers)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.1.2 [Portable code](./TUTORIAL.md#412-portable-code)  
  4.2 [Asynchronous iterators](./TUTORIAL.md#42-asynchronous-iterators)  
  4.3 [Asynchronous context managers](./TUTORIAL.md#43-asynchronous-context-managers)  
  4.4 [Object scope](./TUTORIAL.md#44-object-scope) What happens when an object goes out of scope.  
 5. [Exceptions timeouts and cancellation](./TUTORIAL.md#5-exceptions-timeouts-and-cancellation)  
  5.1 [Exceptions](./TUTORIAL.md#51-exceptions)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.1.1 [Global exception handler](./TUTORIAL.md#511-global-exception-handler)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.1.2 [Keyboard interrupts](./TUTORIAL.md#512-keyboard-interrupts)  
  5.2 [Cancellation and Timeouts](./TUTORIAL.md#52-cancellation-and-timeouts)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.1 [Task cancellation](./TUTORIAL.md#521-task-cancellation)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.2 [Tasks with timeouts](./TUTORIAL.md#522-tasks-with-timeouts)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.3 [Cancelling running tasks](./TUTORIAL.md#523-cancelling-running-tasks) A "gotcha".
 6. [Interfacing hardware](./TUTORIAL.md#6-interfacing-hardware)  
  6.1 [Timing issues](./TUTORIAL.md#61-timing-issues)  
  6.2 [Polling hardware with a task](./TUTORIAL.md#62-polling-hardware-with-a-task)  
  6.3 [Using the stream mechanism](./TUTORIAL.md#63-using-the-stream-mechanism)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6.3.1 [A UART driver example](./TUTORIAL.md#631-a-uart-driver-example)  
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
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7.6.1 [WiFi issues](./TUTORIAL.md#761-wifi-issues)  
  7.7 [CPython compatibility and the event loop](./TUTORIAL.md#77-cpython-compatibility-and-the-event-loop) Compatibility with CPython 3.5+  
  7.8 [Race conditions](./TUTORIAL.md#78-race-conditions)  
  7.9 [Undocumented uasyncio features](./TUTORIAL.md#79-undocumented-uasyncio-features)  
 8. [Notes for beginners](./TUTORIAL.md#8-notes-for-beginners)  
  8.1 [Problem 1: event loops](./TUTORIAL.md#81-problem-1:-event-loops)  
  8.2 [Problem 2: blocking methods](./TUTORIAL.md#8-problem-2:-blocking-methods)  
  8.3 [The uasyncio approach](./TUTORIAL.md#83-the-uasyncio-approach)  
  8.4 [Scheduling in uasyncio](./TUTORIAL.md#84-scheduling-in-uasyncio)  
  8.5 [Why cooperative rather than pre-emptive?](./TUTORIAL.md#85-why-cooperative-rather-than-pre-emptive)  
  8.6 [Communication](./TUTORIAL.md#86-communication)  
 9. [Polling vs Interrupts](./TUTORIAL.md#9-polling-vs-interrupts) A common
 source of confusion.  
 10. [Interfacing threaded code](./TUTORIAL.md#10-interfacing-threaded-code) Taming blocking functions. Multi core coding.  


###### [Main README](../README.md)

# 0. Introduction

Most of this document assumes some familiarity with asynchronous programming.
For those new to it an introduction may be found
[in section 8](./TUTORIAL.md#8-notes-for-beginners).

The MicroPython `uasyncio` library comprises a subset of Python's `asyncio`
library. It is designed for use on microcontrollers. As such it has a small RAM
footprint and fast context switching with zero RAM allocation. This document
describes its use with a focus on interfacing hardware devices. The aim is to
design drivers in such a way that the application continues to run while the
driver is awaiting a response from the hardware. The application remains
responsive to events such as user interaction.

Another major application area for asyncio is in network programming: many
guides to this may be found online.

Note that MicroPython is based on Python 3.4 with additions from later versions.
This version of `uasyncio` supports a subset of CPython 3.8 `asyncio`. This
document identifies supported features. Except where stated program samples run
under MicroPython and CPython 3.8.

This tutorial aims to present a consistent programming style compatible with
CPython V3.8 and above.

## 0.1 Installing uasyncio

Firmware builds after V1.13 incorporate `uasyncio`. The version may be checked
by issuing at the REPL:
```python
import uasyncio
print(uasyncio.__version__)
```
Version 3 will print a version number. Older versions will throw an exception:
installing updated firmware is highly recommended.

###### [Main README](../README.md)

# 1. Cooperative scheduling

The technique of cooperative multi-tasking is widely used in embedded systems.
It offers lower overheads than pre-emptive scheduling and avoids many of the
pitfalls associated with truly asynchronous threads of execution.

###### [Contents](./TUTORIAL.md#contents)

## 1.1 Modules

### 1.1.1 Primitives

The directory `primitives` contains a Python package containing the following:
 * Synchronisation primitives: "micro" versions of CPython's classes.
 * Additional Python primitives including an ISR-compatible version of `Event`
 and a software retriggerable delay class.
 * Primitives for interfacing hardware. These comprise classes for debouncing
 switches and pushbuttons and an asynchronous ADC class. These are documented
 [here](./DRIVERS.md).

To install this Python package copy the `primitives` directory tree and its
contents to your hardware's filesystem. There is no need to copy the `tests`
subdirectory.

### 1.1.2 Demo programs

The directory `as_demos` contains various demo programs implemented as a Python
package. Copy the directory and its contents to the target hardware.

The first two are the most immediately rewarding as they produce visible
results by accessing Pyboard hardware. With all demos, issue ctrl-d between
runs to soft reset the hardware.

 1. [aledflash.py](../as_demos/aledflash.py) Flashes three Pyboard LEDs
 asynchronously for 10s. Requires any Pyboard.
 2. [apoll.py](../as_demos/apoll.py) A device driver for the Pyboard
 accelerometer. Demonstrates the use of a task to poll a device. Runs for 20s.
 Requires a Pyboard V1.x.
 3. [roundrobin.py](../as_demos/roundrobin.py) Demo of round-robin scheduling.
 Also a benchmark of scheduling performance. Runs for 5s on any target.
 4. [auart.py](../as_demos/auart.py) Demo of streaming I/O via a Pyboard UART.
 Requires a link between X1 and X2.
 5. [auart_hd.py](../as_demos/auart_hd.py) Use of the Pyboard UART to communicate
 with a device using a half-duplex protocol e.g. devices such as those using
 the 'AT' modem command set. Link X1-X4, X2-X3.
 6. [gather.py](../as_demos/gather.py) Use of `gather`. Any target.
 7. [iorw.py](../as_demos/iorw.py) Demo of a read/write device driver using the
 stream I/O mechanism. Requires a Pyboard.
 8. [rate.py](../as_demos/rate.py) Benchmark for uasyncio. Any target.

Demos are run using this pattern:
```python
import as_demos.aledflash
```

### 1.1.3 Device drivers

These are installed by copying the `as_drivers` directory and contents to the
target. They have their own documentation as follows:

 1. [A driver for GPS modules](./GPS.md) Runs a background task to
 read and decode NMEA sentences, providing constantly updated position, course,
 altitude and time/date information.
 2. [HTU21D](./HTU21D.md) An I2C temperature and humidity sensor. A task
 periodically queries the sensor maintaining constantly available values.
 3. [NEC IR](./NEC_IR.md) A decoder for NEC IR remote controls. A callback occurs
 whenever a valid signal is received.
 4. [HD44780](./hd44780.md) Driver for common character based LCD displays
 based on the Hitachi HD44780 controller
 5. [I2C](./I2C.md) Use Pyboard I2C slave mode to implement a UART-like
 asynchronous stream interface. Uses: communication with ESP8266,
 or (with coding) interface a Pyboard to I2C masters.

###### [Contents](./TUTORIAL.md#contents)

# 2. uasyncio

The asyncio concept is of cooperative multi-tasking based on coroutines
(coros). A coro is similar to a function but is intended to run concurrently
with other coros. The illusion of concurrency is achieved by periodically
yielding to the scheduler, enabling other coros to be scheduled.

## 2.1 Program structure

Consider the following example:

```python
import uasyncio as asyncio
async def bar():
    count = 0
    while True:
        count += 1
        print(count)
        await asyncio.sleep(1)  # Pause 1s

asyncio.run(bar())
```

Program execution proceeds normally until the call to `asyncio.run(bar())`. At
this point, execution is controlled by the scheduler. A line after
`asyncio.run(bar())` would never be executed. The scheduler runs `bar`
because this has been placed on the scheduler's queue by `asyncio.run(bar())`.
In this trivial example, there is only one task: `bar`. If there were others,
the scheduler would schedule them in periods when `bar` was paused:

```python
import uasyncio as asyncio
async def bar(x):
    count = 0
    while True:
        count += 1
        print('Instance: {} count: {}'.format(x, count))
        await asyncio.sleep(1)  # Pause 1s

async def main():
    for x in range(3):
        asyncio.create_task(bar(x))
    await asyncio.sleep(10)

asyncio.run(main())
```
In this example, three instances of `bar` run concurrently. The
`asyncio.create_task` method returns immediately but schedules the passed coro
for execution. When `main` sleeps for 10s the `bar` instances are scheduled in
turn, each time they yield to the scheduler with `await asyncio.sleep(1)`.

In this instance `main()` terminates after 10s. This is atypical of embedded
`uasyncio` systems. Normally the application is started at power up by a one
line `main.py` and runs forever.

###### [Contents](./TUTORIAL.md#contents)

## 2.2 Coroutines and Tasks

The fundmental building block of `uasyncio` is a coro. This is defined with
`async def` and usually contains at least one `await` statement. This minimal
example waits 1 second before printing a message:

```python
async def bar():
    await asyncio.sleep(1)
    print('Done')
```

V3 `uasyncio` introduced the concept of a `Task`. A `Task` instance is created
from a coro by means of the `create_task` method, which causes the coro to be
scheduled for execution and returns a `Task` instance. In many cases, coros and
tasks are interchangeable: the official docs refer to them as `awaitable`, for
the reason that either of them may be the target of an `await`. Consider this:

```python
import uasyncio as asyncio
async def bar(t):
    print('Bar started: waiting {}secs'.format(t))
    await asyncio.sleep(t)
    print('Bar done')

async def main():
    await bar(1)  # Pauses here until bar is complete
    task = asyncio.create_task(bar(5))
    await asyncio.sleep(0)  # bar has now started
    print('Got here: bar running')  # Can run code here
    await task  # Now we wait for the bar task to complete
    print('All done')
asyncio.run(main())
```
There is a crucial difference between `create_task` and `await`: the former
is synchronous code and returns immediately, with the passed coro being
converted to a `Task` and queued to run "in the background". By contrast,
`await` causes the passed `Task` or coro to run to completion before the next
line executes. Consider these lines of code:

```python
await asyncio.sleep(delay_secs)
await asyncio.sleep(0)
```

The first causes the code to pause for the duration of the delay, with other
tasks being scheduled for this duration. A delay of 0 causes any pending tasks
to be scheduled in round-robin fashion before the following line is run. See
the `roundrobin.py` example.

If a `Task` is run concurrently with `.create_task` it may be cancelled. The
`.create_task` method returns the `Task` instance which may be saved for status
checking or cancellation.

In the following code sample three `Task` instances are created and scheduled
for execution. The "Tasks are running" message is immediately printed. The
three instances of the task `bar` appear to run concurrently. In fact, when one
pauses, the scheduler grants execution to the next, giving the illusion of
concurrency:

```python
import uasyncio as asyncio
async def bar(x):
    count = 0
    while True:
        count += 1
        print('Instance: {} count: {}'.format(x, count))
        await asyncio.sleep(1)  # Pause 1s

async def main():
    for x in range(3):
        asyncio.create_task(bar(x))
    print('Tasks are running')
    await asyncio.sleep(10)

asyncio.run(main())
```

###### [Contents](./TUTORIAL.md#contents)

### 2.2.1 Queueing a task for scheduling

 * `asyncio.create_task` Arg: the coro to run. The scheduler converts the coro
 to a `Task` and queues the task to run ASAP. Return value: the `Task`
 instance. It returns immediately. The coro arg is specified with function call
 syntax with any required arguments passed.
 * `asyncio.run` Arg: the coro to run. Return value: any value returned by the
 passed coro. The scheduler queues the passed coro to run ASAP. The coro arg is
 specified with function call syntax with any required arguments passed. In the
 current version the `run` call returns when the task terminates. However, under
 CPython, the `run` call does not terminate.
 * `await`  Arg: the task or coro to run. If a coro is passed it must be
 specified with function call syntax. Starts the task ASAP. The awaiting task
 blocks until the awaited one has run to completion. As described
 [in section 2.2](./TUTORIAL.md#22-coroutines-and-tasks), it is possible to
 `await` a task which has already been started. In this instance, the `await` is
 on the `task` object (function call syntax is not used).

The above are compatible with CPython 3.8 or above.

###### [Contents](./TUTORIAL.md#contents)

### 2.2.2 Running a callback function

Callbacks should be Python functions designed to complete in a short period of
time. This is because tasks will have no opportunity to run for the
duration. If it is necessary to schedule a callback to run after `t` seconds,
it may be done as follows:
```python
async def schedule(cb, t, *args, **kwargs):
    await asyncio.sleep(t)
    cb(*args, **kwargs)
```
In this example the callback runs after three seconds:
```python
import uasyncio as asyncio

async def schedule(cbk, t, *args, **kwargs):
    await asyncio.sleep(t)
    cbk(*args, **kwargs)

def callback(x, y):
    print('x={} y={}'.format(x, y))

async def bar():
    asyncio.create_task(schedule(callback, 3, 42, 100))
    for count in range(6):
        print(count)
        await asyncio.sleep(1)  # Pause 1s

asyncio.run(bar())
```

###### [Contents](./TUTORIAL.md#contents)

### 2.2.3 Notes

Coros may be bound methods. A coro usually contains at least one `await`
statement, but nothing will break (in MicroPython or CPython 3.8) if it has
none.

Similarly to a function or method, a coro can contain a `return` statement. To
retrieve the returned data issue:

```python
result = await my_task()
```

It is possible to await completion of a set of multiple asynchronously running
tasks, accessing the return value of each. This is done by
[uasyncio.gather](./TUTORIAL.md#33-gather) which launches the tasks and pauses
until the last terminates. It returns a list containing the data returned by
each task:
```python
import uasyncio as asyncio

async def bar(n):
    for count in range(n):
        await asyncio.sleep_ms(200 * n)  # Pause by varying amounts
    print('Instance {} stops with count = {}'.format(n, count))
    return count * count

async def main():
    tasks = (bar(2), bar(3), bar(4))
    print('Waiting for gather...')
    res = await asyncio.gather(*tasks)
    print(res)

asyncio.run(main())
```

###### [Contents](./TUTORIAL.md#contents)

### 2.2.4 A typical firmware app

Most firmware applications run forever. This requires the coro passed to
`asyncio.run()` to `await` a non-terminating coro.

To ease debugging, and for CPython compatibility, some "boilerplate" code is
suggested in the sample below.

By default, an exception in a task will not stop the application as a whole from
running. This can make debugging difficult. The fix shown below is discussed
[in 5.1.1](./TUTORIAL.md#511-global-exception-handler).

It is bad practice to create a task prior to issuing `asyncio.run()`. CPython
will throw an exception in this case. MicroPython
[does not](https://github.com/micropython/micropython/issues/6174), but it's
wise to avoid doing this.

Lastly, `uasyncio` retains state. This means that, by default, you need to
reboot between runs of an application. This can be fixed with the
`new_event_loop` method discussed
[in 7.2](./TUTORIAL.md#72-uasyncio-retains-state).

These considerations suggest the following application structure:
```python
import uasyncio as asyncio
from my_app import MyClass

def set_global_exception():
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        sys.exit()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

async def main():
    set_global_exception()  # Debug aid
    my_class = MyClass()  # Constructor might create tasks
    asyncio.create_task(my_class.foo())  # Or you might do this
    await my_class.run_forever()  # Non-terminating method
try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()  # Clear retained state
```

###### [Contents](./TUTORIAL.md#contents)

## 2.3 Delays

Where a delay is required in a task there are two options. For longer delays and
those where the duration need not be precise, the following should be used:

```python
async def foo(delay_secs, delay_ms):
    await asyncio.sleep(delay_secs)
    print('Hello')
    await asyncio.sleep_ms(delay_ms)
```

While these delays are in progress the scheduler will schedule other tasks.
This is generally highly desirable, but it does introduce uncertainty in the
timing as the calling routine will only be rescheduled when the one running at
the appropriate time has yielded. The amount of latency depends on the design
of the application, but is likely to be on the order of tens or hundreds of ms;
this is discussed further in [Section 6](./TUTORIAL.md#6-interfacing-hardware).

Very precise delays may be issued by using the `utime` functions `sleep_ms`
and `sleep_us`. These are best suited for short delays as the scheduler will
be unable to schedule other tasks while the delay is in progress.

###### [Contents](./TUTORIAL.md#contents)

# 3 Synchronisation

There is often a need to provide synchronisation between tasks. A common
example is to avoid what are known as "race conditions" where multiple tasks
compete to access a single resource. These are discussed
[in section 7.8](./TUTORIAL.md#78-race-conditions). Another hazard is the
"deadly embrace" where two tasks each wait on the other's completion.

Another synchronisation issue arises with producer and consumer tasks. The
producer generates data which the consumer uses. Asyncio provides the `Queue`
object. The producer puts data onto the queue while the consumer waits for its
arrival (with other tasks getting scheduled for the duration). The `Queue`
guarantees that items are removed in the order in which they were received.
Alternatively, a `Barrier` instance can be used if the producer must wait
until the consumer is ready to access the data.

In simple applications, communication may be achieved with global flags or bound
variables. A more elegant approach is to use synchronisation primitives.
CPython provides the following classes:  
 * `Lock` - already incorporated in new `uasyncio`.
 * `Event` - already incorporated.
 * `ayncio.gather` - already incorporated.
 * `Semaphore` In this repository.
 * `BoundedSemaphore`. In this repository.
 * `Condition`. In this repository.
 * `Queue`. In this repository.

As the table above indicates, not all are yet officially supported. In the
interim, implementations may be found in the `primitives` directory. The
following classes which are non-standard, are also in that directory:
 * `Message` An ISR-friendly `Event` with an optional data payload.
 * `Barrier` Based on a Microsoft class, enables multiple coros to synchronise
 in a similar (but not identical) way to `gather`.
 * `Delay_ms` A useful software-retriggerable monostable, akin to a watchdog.
 Calls a user callback if not cancelled or regularly retriggered.

A further set of primitives for synchronising hardware are detailed in
[section 3.9](./TUTORIAL.md#39-synchronising-to-hardware).

To install the primitives, copy the `primitives` directory and contents to the
target. A primitive is loaded by issuing (for example):
```python
from primitives import Semaphore, BoundedSemaphore
from primitives import Queue
```
When `uasyncio` acquires official versions of the CPython primitives, the
invocation lines alone should be changed. E.g.:
```python
from uasyncio import Semaphore, BoundedSemaphore
from uasyncio import Queue
```
##### Note on CPython compatibility

CPython will throw a `RuntimeError` on first use of a synchronisation primitive
that was instantiated prior to starting the scheduler. By contrast,
`MicroPython` allows instantiation in synchronous code executed before the
scheduler is started. Early instantiation can be advantageous in low resource
environments. For example, a class might have a large buffer and bound `Event`
instances. Such a class should be instantiated early, before RAM fragmentation
sets in.

The following provides a discussion of the primitives.

###### [Contents](./TUTORIAL.md#contents)

## 3.1 Lock

This describes the use of the official `Lock` primitive.

This guarantees unique access to a shared resource. In the following code
sample a `Lock` instance `lock` has been created and is passed to all tasks
wishing to access the shared resource. Each task attempts to acquire the lock,
pausing execution until it succeeds.

```python
import uasyncio as asyncio
from uasyncio import Lock

async def task(i, lock):
    while 1:
        await lock.acquire()
        print("Acquired lock in task", i)
        await asyncio.sleep(0.5)
        lock.release()

async def main():
    lock = Lock()  # The Lock instance
    for n in range(1, 4):
        asyncio.create_task(task(n, lock))
    await asyncio.sleep(10)

asyncio.run(main())  # Run for 10s
```

Methods:

 * `locked` No args. Returns `True` if locked.
 * `release` No args. Releases the lock.
 * `acquire` No args. Coro which pauses until the lock has been acquired. Use
 by executing `await lock.acquire()`.

A task waiting on a lock may be cancelled or may be run subject to a timeout.
The normal way to use a `Lock` is in a context manager:

```python
import uasyncio as asyncio
from uasyncio import Lock

async def task(i, lock):
    while 1:
        async with lock:
            print("Acquired lock in task", i)
            await asyncio.sleep(0.5)
 
async def main():
    lock = Lock()  # The Lock instance
    for n in range(1, 4):
        asyncio.create_task(task(n, lock))
    await asyncio.sleep(10)

asyncio.run(main())  # Run for 10s
```

###### [Contents](./TUTORIAL.md#contents)

## 3.2 Event

This describes the use of the official `Event` primitive.

This provides a way for one or more tasks to pause until another one flags them to
continue. An `Event` object is instantiated and made accessible to all tasks
using it:

```python
import uasyncio as asyncio
from uasyncio import Event

async def waiter(event):
    print('Waiting for event')
    await event.wait()  # Pause here until event is set
    print('Waiter got event.')
    event.clear()  # Flag caller and enable re-use of the event

async def main():
    event = Event()
    asyncio.create_task(waiter(event))
    await asyncio.sleep(2)
    print('Setting event')
    event.set()
    await asyncio.sleep(1)
    # Caller can check if event has been cleared
    print('Event is {}'.format('set' if event.is_set() else 'clear'))

asyncio.run(main())
```
Constructor: no args.  
Synchronous Methods:
 * `set` Initiates the event.
 * `clear` No args. Clears the event.
 * `is_set` No args. Returns `True` if the event is set.

Asynchronous Method:
 * `wait` Pause until event is set.

Tasks wait on the event by issuing `await event.wait()`; execution pauses until
another one issues `event.set()`. This causes all tasks waiting on the `Event` to
be queued for execution. Note that the synchronous sequence
```python
event.set()
event.clear()
```
will cause any tasks waiting on the event to resume in round-robin order. In
general, the waiting task should clear the event, as in the `waiter` example
above. This caters for the case where the waiting task has not reached the
event at the time when it is triggered. In this instance, by the time the task
reaches the event, the task will find it clear and will pause. This can lead to
non-deterministic behaviour if timing is marginal.

The `Event` class is an efficient and effective way to synchronise tasks, but
firmware applications often have multiple tasks running `while True:` loops.
The number of `Event` instances required to synchronise these can multiply.
Consider the case of one producer task feeding N consumers. The producer sets
an `Event` to tell the consumer that data is ready; it then needs to wait until
all consumers have completed before triggering them again. Consider these
approaches:
 1. Each consumer sets an `Event` on completion. Producer waits until all
 `Event`s are set before clearing them and setting its own `Event`.
 2. Consumers do not loop, running to completion. Producer uses `gather` to
 instantiate consumer tasks and wait on their completion.
 3. `Event` instances are replaced with a single [Barrier](./TUTORIAL.md#37-barrier)
 instance.

Solution 1 suffers a proliferation of `Event`s and suffers an inefficient
busy-wait where the producer waits on N events. Solution 2 is inefficient with
constant creation of tasks. Arguably the `Barrier` class is the best approach.

**WARNING**  
`Event` methods must not be called from an interrupt service routine (ISR). The
`Event` class is not thread safe. See [ThreadSafeFlag](./TUTORIAL.md#36-threadsafeflag).

### 3.2.1 Wait on multiple events

The `WaitAny` primitive allows a task to wait on a list of events. When one
of the events is triggered, the task continues. It is effectively a logical
`or` of events.
```python
from primitives import WaitAny
evt1 = Event()
evt2 = Event()
# Launch tasks that might trigger these events
evt = await WaitAny((evt1, evt2)).wait()
# One or other was triggered
if evt is evt1:
    evt1.clear()
    # evt1 was triggered
else:
    evt2.clear()
    # evt2 was triggered
```
The `WaitAll` primitive is similar except that the calling task will pause
until all passed `Event`s have been set:
```python
from primitives import WaitAll
evt1 = Event()
evt2 = Event()
wa = WaitAll((evt1, evt2)).wait() 
# Launch tasks that might trigger these events
await wa
# Both were triggered
```
Awaiting `WaitAll` or `WaitAny` may be cancelled or subject to a timeout.

###### [Contents](./TUTORIAL.md#contents)

## 3.3 Coordinating multiple tasks

Several tasks may be launched together with the launching task pausing until
all have completed. The `gather` mechanism is supported by CPython and
MicroPython. CPython 3.11 adds a `TaskGroup` class which is particularly
suited to applications where runtime exceptions may be encountered. It is not
yet officially supported by MicroPython.

### 3.3.1 gather

This official `uasyncio` asynchronous method causes a number of tasks to run,
pausing until all have either run to completion or been terminated by
cancellation or timeout. It returns a list of the return values of each task.

Its call signature is
```python
res = await asyncio.gather(*tasks, return_exceptions=False)
```
The keyword-only boolean arg `return_exceptions` determines the behaviour in
the event of a cancellation or timeout of tasks. If `False`, the `gather`
terminates immediately, raising the relevant exception which should be trapped
by the caller. If `True`, the `gather` continues to pause until all have either
run to completion or been terminated by cancellation or timeout. In this case,
tasks which have been terminated will return the exception object in the list
of return values.

The following script may be used to demonstrate this behaviour:

```python
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

async def barking(n):
    print('Start barking')
    for _ in range(6):
        await asyncio.sleep(1)
    print('Done barking.')
    return 2 * n

async def foo(n):
    print('Start timeout coro foo()')
    while True:
        await asyncio.sleep(1)
        n += 1
    return n

async def bar(n):
    print('Start cancellable bar()')
    while True:
        await asyncio.sleep(1)
        n += 1
    return n

async def do_cancel(task):
    await asyncio.sleep(5)
    print('About to cancel bar')
    task.cancel()

async def main():
    tasks = [asyncio.create_task(bar(70))]
    tasks.append(barking(21))
    tasks.append(asyncio.wait_for(foo(10), 7))
    asyncio.create_task(do_cancel(tasks[0]))
    res = None
    try:
        res = await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.TimeoutError:  # These only happen if return_exceptions is False
        print('Timeout')  # With the default times, cancellation occurs first
    except asyncio.CancelledError:
        print('Cancelled')
    print('Result: ', res)

asyncio.run(main())
```
### 3.3.2 TaskGroups

The `TaskGroup` class is unofficially provided by
[this PR](https://github.com/micropython/micropython/pull/8791). It is well
suited to applications where one or more of a group of tasks is subject to
runtime exceptions. A `TaskGroup` is instantiated in an asynchronous context
manager. The `TaskGroup` instantiates member tasks. When all have run to
completion, the context manager terminates. Return values from member tasks
cannot be retrieved. Results should be passed in other ways such as via bound
variables, queues etc.

An exception in a member task not trapped by that task is propagated to the
task that created the `TaskGroup`. All tasks in the `TaskGroup` then terminate
in an orderly fashion: cleanup code in any `finally` clause will run. When all
cleanup code has completed, the context manager completes, and execution passes
to an exception handler in an outer scope.

If a member task is cancelled in code, that task terminates in an orderly way
but the other members continue to run.

The following illustrates the basic salient points of using a `TaskGroup`:
```python
import uasyncio as asyncio
async def foo(n):
    for x in range(10 + n):
        print(f"Task {n} running.")
        await asyncio.sleep(1 + n/10)
    print(f"Task {n} done")

async def main():
    async with asyncio.TaskGroup() as tg:  # Context manager pauses until members terminate
        for n in range(4):
            tg.create_task(foo(n))  # tg.create_task() creates a member task
    print("TaskGroup done")  # All tasks have terminated

asyncio.run(main())
```
This more complete example illustrates an exception which is not trapped by the
member task. Cleanup code on all members runs when the exception occurs,
followed by exception handling code in `main()`.
```python
import uasyncio as asyncio
fail = True  # Set False to demo normal completion
async def foo(n):
    print(f"Task {n} running...")
    try:
        for x in range(10 + n):
            await asyncio.sleep(1 + n/10)
            if n==0 and x==5 and fail:
                raise OSError("Uncaught exception in task.")
        print(f"Task {n} done")
    finally:
        print(f"Task {n} cleanup")

async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            for n in range(4):
                tg.create_task(foo(n))
        print("TaskGroup done")  # Does not get here if a task throws exception
    except Exception as e:
        print(f'TaskGroup caught exception: "{e}"')
    finally:
        print("TaskGroup finally")

asyncio.run(main())
```

###### [Contents](./TUTORIAL.md#contents)

## 3.4 Semaphore

This is currently an unofficial implementation. Its API is as per CPython
asyncio.

A semaphore limits the number of tasks which can access a resource. It can be
used to limit the number of instances of a particular task which can run
concurrently. It performs this using an access counter which is initialised by
the constructor and decremented each time a task acquires the semaphore.

Constructor: Optional arg `value` default 1. Number of permitted concurrent
accesses.

Synchronous method:
 * `release` No args. Increments the access counter.

Asynchronous method:
 * `acquire` No args. If the access counter is greater than 0, decrements it
 and terminates. Otherwise waits for it to become greater than 0 before
 decrementing it and terminating.

The easiest way to use it is with an asynchronous context manager. The
following illustrates tasks accessing a resource one at a time:

```python
import uasyncio as asyncio
from primitives import Semaphore

async def foo(n, sema):
    print('foo {} waiting for semaphore'.format(n))
    async with sema:
        print('foo {} got semaphore'.format(n))
        await asyncio.sleep_ms(200)

async def main():
    sema = Semaphore()
    for num in range(3):
        asyncio.create_task(foo(num, sema))
    await asyncio.sleep(2)

asyncio.run(main())
```

There is a difference between a `Semaphore` and a `Lock`. A `Lock` instance is
owned by the coro which locked it: only that coro can release it. A
`Semaphore` can be released by any coro which acquired it.

###### [Contents](./TUTORIAL.md#contents)

### 3.4.1 BoundedSemaphore

This is currently an unofficial implementation. Its API is as per CPython
asyncio.

This works identically to the `Semaphore` class except that if the `release`
method causes the access counter to exceed its initial value, a `ValueError`
is raised.

###### [Contents](./TUTORIAL.md#contents)

## 3.5 Queue

Queue objects provide a means of synchronising producer and consumer tasks: the
producer puts data items onto the queue with the consumer removing them. If the
queue becomes full, the producer task will block, likewise if the queue becomes
empty the consumer will block. Some queue implementations allow producer and
consumer to run in different contexts: for example where one runs in an
interrupt service routine or on a different thread or core from the `uasyncio`
application. Such a queue is termed "thread safe".

The `Queue` class is an unofficial implementation whose API is a subset of that
of CPython's `asyncio.Queue`. Like `asyncio.Queue` this class is not thread
safe. A queue class optimised for MicroPython is presented in
[Ringbuf queue](./EVENTS.md#7-ringbuf-queue). A thread safe version is
documented in [ThreadSafeQueue](./THREADING.md#22-threadsafequeue).

Constructor:  
Optional arg `maxsize=0`. If zero, the queue can grow without limit subject to
heap size. If `maxsize>0` the queue's size will be constrained.

Synchronous methods (immediate return):  
 * `qsize` No arg. Returns the number of items in the queue.
 * `empty` No arg. Returns `True` if the queue is empty.
 * `full` No arg. Returns `True` if the queue is full.
 * `put_nowait` Arg: the object to put on the queue. Raises an exception if the
 queue is full.
 * `get_nowait` No arg. Returns an object from the queue. Raises an exception
 if the queue is empty.

Asynchronous methods:  
 * `put` Arg: the object to put on the queue. If the queue is full, it will
 block until space is available.
 * `get` No arg. Returns an object from the queue. If the queue is empty, it
 will block until an object is put on the queue.

```python
import uasyncio as asyncio
from primitives import Queue

async def slow_process():
    await asyncio.sleep(2)
    return 42

async def produce(queue):
    print('Waiting for slow process.')
    result = await slow_process()
    print('Putting result onto queue')
    await queue.put(result)  # Put result on queue

async def consume(queue):
    print("Running consume()")
    result = await queue.get()  # Blocks until data is ready
    print('Result was {}'.format(result))

async def queue_go(delay):
    queue = Queue()
    asyncio.create_task(consume(queue))
    asyncio.create_task(produce(queue))
    await asyncio.sleep(delay)
    print("Done")

asyncio.run(queue_go(4))
```

###### [Contents](./TUTORIAL.md#contents)

## 3.6 ThreadSafeFlag

See also [Interfacing uasyncio to interrupts](./INTERRUPTS.md). Because of
[this issue](https://github.com/micropython/micropython/issues/7965) the
`ThreadSafeFlag` class does not work under the Unix build.

This official class provides an efficient means of synchronising a task with a
truly asynchronous event such as a hardware interrupt service routine or code
running in another thread or on another core. It operates in a similar way to
`Event` with the following key differences:
 * It is thread safe: the `set` event may be called from asynchronous code.
 * It is self-clearing.
 * Only one task may wait on the flag.

Synchronous method:
 * `set` Triggers the flag. Like issuing `set` then `clear` to an `Event`.

Asynchronous method:
 * `wait` Wait for the flag to be set. If the flag is already set then it
 returns immediately.

Typical usage is having a `uasyncio` task wait on a hard ISR. Only one task
should wait on a `ThreadSafeFlag`. The hard ISR services the interrupting
device, sets the `ThreadSafeFlag`, and quits. A single task waits on the flag.
This design conforms with the self-clearing behaviour of the `ThreadSafeFlag`.
Each interrupting device has its own `ThreadSafeFlag` instance and its own
waiting task.
```python
import uasyncio as asyncio
from pyb import Timer

tsf = asyncio.ThreadSafeFlag()

def cb(_):
    tsf.set()

async def foo():
    while True:
        await tsf.wait()
        # Could set an Event here to trigger multiple tasks
        print('Triggered')

tim = Timer(1, freq=1, callback=cb)

asyncio.run(foo())
```
An example [based on one posted by Damien](https://github.com/micropython/micropython/pull/6886#issuecomment-779863757)  
Link pins X1 and X2 to test.
```python
from machine import Pin, Timer
import uasyncio as asyncio

class AsyncPin:
    def __init__(self, pin, trigger):
        self.pin = pin
        self.flag = asyncio.ThreadSafeFlag()
        self.pin.irq(lambda pin: self.flag.set(), trigger, hard=True)

    async def wait_edge(self):
        await self.flag.wait()

async def foo():
    pin_in = Pin('X1', Pin.IN)
    async_pin = AsyncPin(pin_in, Pin.IRQ_RISING)
    pin_out = Pin('X2', Pin.OUT)  # Toggle pin to test
    t = Timer(-1, period=500, callback=lambda _: pin_out(not pin_out()))
    await asyncio.sleep(0)
    while True:
        await async_pin.wait_edge()
        print('Got edge.')

asyncio.run(foo())
```

The current implementation provides no performance benefits against polling the
hardware: other pending tasks may be granted execution first in round-robin
fashion. However the `ThreadSafeFlag` uses the I/O mechanism. There is a plan
to provide a means to reduce the latency such that selected I/O devices are
polled every time the scheduler acquires control. This will provide the highest
possible level of performance as discussed in
[Polling vs Interrupts](./TUTORIAL.md#9-polling-vs-interrupts).

Regardless of performance issues, a key use for `ThreadSafeFlag` is where a
hardware device requires the use of an ISR for a μs level response. Having
serviced the device, the ISR flags an asynchronous routine, typically
processing received data.

See [Threadsafe Event](./THREADING.md#31-threadsafe-event) for a thread safe
class which allows multiple tasks to wait on it.

###### [Contents](./TUTORIAL.md#contents)

## 3.7 Barrier

This is an unofficial implementation of a primitive supported in
[CPython 3.11](https://docs.python.org/3.11/library/asyncio-sync.html#asyncio.Barrier).
While similar in purpose to `gather` there are differences described below.

Its principal purpose is to cause multiple coros to rendezvous at a particular
point. For example producer and consumer coros can synchronise at a point where
the producer has data available and the consumer is ready to use it. At that
point in time, the `Barrier` can optionally run a callback before releasing the
barrier to allow all waiting coros to continue.

Secondly, it can allow a task to pause until one or more other tasks have
terminated or passed a particular point. For example an application might want
to shut down various peripherals before starting a sleep period. The task
wanting to sleep initiates several shut down tasks and waits until they have
triggered the barrier to indicate completion. This use case may also be served
by `gather`.

The key difference between `Barrier` and `gather` is symmetry: `gather` is
asymmetrical. One task owns the `gather` and awaits completion of a set of
tasks. By contrast, `Barrier` can be used symmetrically with member tasks
pausing until all have reached the barrier. This makes it suited for use in
the `while True:` constructs common in firmware applications. Use of `gather`
would imply instantiating a set of tasks on every pass of the loop.

`gather` provides access to return values; irrelevant to `Barrier` because
passing a barrier does not imply return. `Barrier` now has an efficient
implementation using `Event` to suspend waiting tasks.

The following is a typical usage example. A data provider acquires data from
some hardware and transmits it concurrently on a number of interfaces. These
run at different speeds. The `Barrier` synchronises these loops. This can run
on a Pyboard.
```python
import uasyncio as asyncio
from primitives import Barrier
from machine import UART
import ujson

data = None
async def provider(barrier):
    global data
    n = 0
    while True:
        n += 1  # Get data from some source
        data = ujson.dumps([n, 'the quick brown fox jumps over the lazy dog'])
        print('Provider triggers senders')
        await barrier  # Free sender tasks
        print('Provider waits for last sender to complete')
        await barrier

async def sender(barrier, swriter, n):
    while True:
        await barrier  # Provider has got data
        swriter.write(data)
        await swriter.drain()
        print('UART', n, 'sent', data)
        await barrier  # Trigger provider when last sender has completed

async def main():
    sw1 = asyncio.StreamWriter(UART(1, 9600), {})
    sw2 = asyncio.StreamWriter(UART(2, 1200), {})
    barrier = Barrier(3)
    for n, sw in enumerate((sw1, sw2)):
        asyncio.create_task(sender(barrier, sw, n + 1))
    await provider(barrier)

asyncio.run(main())
```

Constructor.  
Mandatory arg:  
 * `participants` The number of coros which will use the barrier.  
Optional args:  
 * `func` Callback or coroutine to run. Default `None`.  
 * `args` Tuple of args for the callback. Default `()`.

Public synchronous methods:  
 * `busy` No args. Returns `True` if at least one task is waiting on the
 barrier.
 * `trigger` No args. The barrier records that the coro has passed the critical
 point. Returns "immediately".
 * `result` No args. If a callback was provided, returns the return value from
 the callback. If a coro, returns the `Task` instance. See below.

The callback can be a function or a coro. Typically a function will be used; it
must run to completion beore the barrier is released. A coro will be promoted
to a `Task` and run asynchronously. The `Task` may be retrieved (e.g. for
cancellation) using the `result` method.

If a coro waits on a barrier, it should issue an `await` prior to accessing the
`result` method. To guarantee that the callback has run it is necessary to wait
until all participant coros have passed the barrier.

Participant coros issue `await my_barrier` whereupon execution pauses until all
other participants are also waiting on it. At this point any callback will run
and then each participant will re-commence execution. See `barrier_test` and
`semaphore_test` in `asyntest.py` for example usage.

A special case of `Barrier` usage is where some coros are allowed to pass the
barrier, registering the fact that they have done so. At least one coro must
wait on the barrier. That coro will pause until all non-waiting coros have
passed the barrier, and all waiting coros have reached it. At that point all
waiting coros will resume. A non-waiting coro issues `barrier.trigger()` to
indicate that is has passed the critical point.

###### [Contents](./TUTORIAL.md#contents)

## 3.8 Delay_ms class

This implements the software equivalent of a retriggerable monostable or a
watchdog timer. It has an internal boolean `running` state. When instantiated
the `Delay_ms` instance does nothing, with `running` `False` until triggered.
Then `running` becomes `True` and a timer is initiated. This can be prevented
from timing out by triggering it again (with a new timeout duration). So long
as it is triggered before the time specified in the preceeding trigger it will
never time out.

If it does time out the `running` state will revert to `False`. This can be
interrogated by the object's `running()` method. In addition a `callable` can
be specified to the constructor. A `callable` can be a callback or a coroutine.
A callback will execute when a timeout occurs; where the `callable` is a
coroutine it will be converted to a `Task` and run asynchronously.

Constructor arguments (defaults in brackets):

 1. `func` The `callable` to call on timeout (default `None`).
 2. `args` A tuple of arguments for the `callable` (default `()`).
 3. `can_alloc` Unused arg, retained to avoid breaking code.
 4. `duration` Integer, default 1000 ms. The default timer period where no value
 is passed to the `trigger` method.

Synchronous methods:

 1. `trigger` optional argument `duration=0`. A timeout will occur after
 `duration` ms unless retriggered. If no arg is passed the period will be that
 of the `duration` passed to the constructor. The method can be called from a
 hard or soft ISR. It is now valid for `duration` to be less than the current
 time outstanding.
 2. `stop` No argument. Cancels the timeout, setting the `running` status
 `False`. The timer can be restarted by issuing `trigger` again. Also clears
 the `Event` described in `wait` below.
 3. `running` No argument. Returns the running status of the object.
 4. `__call__` Alias for running.
 5. `rvalue` No argument. If a timeout has occurred and a callback has run,
 returns the return value of the callback. If a coroutine was passed, returns
 the `Task` instance. This allows the `Task` to be cancelled or awaited.
 6. `callback` args `func=None`, `args=()`. Allows the callable and its args to
 be assigned, reassigned or disabled at run time.
 7. `deinit` No args. Cancels the running task. See [Object scope](./TUTORIAL.md#44-object-scope).
 8. `clear` No args. Clears the `Event` described in `wait` below.
 9. `set` No args. Sets the `Event` described in `wait` below.

Asynchronous method:
 1. `wait` One or more tasks may wait on a `Delay_ms` instance. Pause until the
 delay instance has timed out.

In this example a `Delay_ms` instance is created with the default duration of
1 sec. It is repeatedly triggered for 5 secs, preventing the callback from
running. One second after the triggering ceases, the callback runs.

```python
import uasyncio as asyncio
from primitives import Delay_ms

async def my_app():
    d = Delay_ms(callback, ('Callback running',))
    print('Holding off callback')
    for _ in range(10):  # Hold off for 5 secs
        await asyncio.sleep_ms(500)
        d.trigger()
    print('Callback will run in 1s')
    await asyncio.sleep(2)
    print('Done')

def callback(v):
    print(v)

try:
    asyncio.run(my_app())
finally:
    asyncio.new_event_loop()  # Clear retained state
```
This example illustrates multiple tasks waiting on a `Delay_ms`. No callback is
used.
```python
import uasyncio as asyncio
from primitives import Delay_ms

async def foo(n, d):
    await d.wait()
    d.clear()  # Task waiting on the Event must clear it
    print('Done in foo no.', n)

async def my_app():
    d = Delay_ms()
    for n in range(4):
        asyncio.create_task(foo(n, d))
    d.trigger(3000)
    print('Waiting on d')
    await d.wait()
    print('Done in my_app.')
    await asyncio.sleep(1)
    print('Test complete.')

try:
    asyncio.run(my_app())
finally:
    _ = asyncio.new_event_loop()  # Clear retained state
```

## 3.9 Message

The `Message` class uses [ThreadSafeFlag](./TUTORIAL.md#36-threadsafeflag) to
provide an object similar to `Event` with the following differences:

 * `.set()` has an optional data payload.
 * `.set()` can be called from another thread, another core, or from an ISR.
 * It is an awaitable class.
 * Payloads may be retrieved in an asynchronous iterator.
 * Multiple tasks can wait on a single `Message` instance.

It may be found in the `threadsafe` directory and is documented
[here](./THREADING.md#32-message).

## 3.10 Synchronising to hardware

The following hardware-related classes are documented [here](./DRIVERS.md):
 * `Switch` A debounced switch which can trigger open and close user callbacks.
 * `Pushbutton` Debounced pushbutton with callbacks for pressed, released, long
 press or double-press.
 * `ESP32Touch` Extends `Pushbutton` class to support ESP32 touchpads.
 * `Encoder` An asynchronous interface for control knobs with switch contacts
 configured as a quadrature encoder.
 * `AADC` Asynchronous ADC. A task can pause until the value read from an ADC
 goes outside defined bounds. Bounds can be absolute or relative to the current
 value.

###### [Contents](./TUTORIAL.md#contents)

# 4 Designing classes for asyncio

In the context of device drivers, the aim is to ensure nonblocking operation.
The design should ensure that other tasks get scheduled in periods while the
driver is waiting for the hardware. For example, a task awaiting data arriving
on a UART or a user pressing a button should allow other tasks to be scheduled
until the event occurs.

###### [Contents](./TUTORIAL.md#contents)

## 4.1 Awaitable classes

A task can pause execution by waiting on an `awaitable` object. There is a
difference between CPython and MicroPython in the way an `awaitable` class is
defined: see [Portable code](./TUTORIAL.md#412-portable-code) for a way to
write a portable class. This section describes a simpler MicroPython specific
solution.

In the following code sample, the `__iter__` special method runs for a period.
The calling coro blocks, but other coros continue to run. The key point is that
`__iter__` uses `yield from` to yield execution to another coro, blocking until
it has completed.

```python
import uasyncio as asyncio

class Foo():
    def __iter__(self):
        for n in range(5):
            print('__iter__ called')
            yield from asyncio.sleep(1) # Other tasks get scheduled here
        return 42

async def bar():
    foo = Foo()  # Foo is an awaitable class
    print('waiting for foo')
    res = await foo  # Retrieve result
    print('done', res)

asyncio.run(bar())
```

### 4.1.1 Use in context managers

Awaitable objects can be used in synchronous or asynchronous CM's by providing
the necessary special methods. The syntax is:

```python
with await awaitable as a:  # The 'as' clause is optional
    # code omitted
async with awaitable as a:  # Asynchronous CM (see below)
    # do something
```

To achieve this, the `__await__` generator should return `self`. This is passed
to any variable in an `as` clause and also enables the special methods to work.

###### [Contents](./TUTORIAL.md#contents)

### 4.1.2 Portable code

The Python language requires that `__await__` is a generator function. In
MicroPython generators and tasks are identical, so the solution is to use
`yield from task(args)`.

This tutorial aims to offer code portable to CPython 3.8 or above. In CPython
tasks and generators are distinct. CPython tasks have an `__await__` special
method which retrieves a generator. This is portable and was tested under
CPython 3.8:

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

asyncio.run(bar())
```

In `__await__`, `yield from asyncio.sleep(1)` was allowed in CPython 3.6. In
V3.8 it produces a syntax error. It must now be put in the task as in the above
example.

###### [Contents](./TUTORIAL.md#contents)

## 4.2 Asynchronous iterators

These provide a means of returning a finite or infinite sequence of values
and could be used as a means of retrieving successive data items as they arrive
from a read-only device. An asynchronous iterable calls asynchronous code in
its `next` method. The class must conform to the following requirements:

 * It has an `__aiter__` method returning the asynchronous iterator.
 * It has an ` __anext__` method which is a task - i.e. defined with
 `async def` and containing at least one `await` statement. To stop
 the iteration, it must raise a `StopAsyncIteration` exception.

Successive values are retrieved with `async for` as below:

```python
import uasyncio as asyncio
class AsyncIterable:
    def __init__(self):
        self.data = (1, 2, 3, 4, 5)
        self.index = 0

    def __aiter__(self):  # See note below
        return self

    async def __anext__(self):
        data = await self.fetch_data()
        if data:
            return data
        else:
            raise StopAsyncIteration

    async def fetch_data(self):
        await asyncio.sleep(0.1)  # Other tasks get to run
        if self.index >= len(self.data):
            return None
        x = self.data[self.index]
        self.index += 1
        return x

async def run():
    ai = AsyncIterable()
    async for x in ai:
        print(x)
asyncio.run(run())
```
The `__aiter__` method was formerly an asynchronous method. CPython 3.6 accepts
synchronous or asynchronous methods. CPython 3.8 and MicroPython require
synchronous code [ref](https://github.com/micropython/micropython/pull/6272).

Asynchronous comprehensions [PEP530](https://www.python.org/dev/peps/pep-0530/),
supported in CPython 3.6, are not yet supported in MicroPython.

###### [Contents](./TUTORIAL.md#contents)

## 4.3 Asynchronous context managers

Classes can be designed to support asynchronous context managers. These are
CM's having enter and exit procedures which are tasks. An example is the `Lock`
class. Such a class has an `__aenter__` task which is logically required to run
asynchronously. To support the asynchronous CM protocol its `__aexit__` method
also must be a task. Such classes are accessed from within a task with the
following syntax:
```python
async def bar(lock):
    async with lock as obj:  # "as" clause is optional, no real point for a lock
        print('In context manager')
```
As with normal context managers an exit method is guaranteed to be called when
the context manager terminates, whether normally or via an exception. To
achieve this, the special methods `__aenter__` and `__aexit__` must be
defined, both being tasks waiting on a task or `awaitable` object. This example
comes from the `Lock` class:
```python
    async def __aenter__(self):
        await self.acquire()  # a coro defined with async def
        return self

    async def __aexit__(self, *args):
        self.release()  # A synchronous method
```
If the `async with` has an `as variable` clause the variable receives the
value returned by `__aenter__`. The following is a complete example:
```python
import uasyncio as asyncio

class Foo:
    def __init__(self):
        self.data = 0

    async def acquire(self):
        await asyncio.sleep(1)
        return 42

    async def __aenter__(self):
        print('Waiting for data')
        self.data = await self.acquire()
        return self

    def close(self):
        print('Exit')

    async def __aexit__(self, *args):
        print('Waiting to quit')
        await asyncio.sleep(1)  # Can run asynchronous
        self.close()  # or synchronous methods

async def bar():
    foo = Foo()
    async with foo as f:
        print('In context manager')
        res = f.data
    print('Done', res)

asyncio.run(bar())
```

###### [Contents](./TUTORIAL.md#contents)

## 4.4 Object scope

If an object launches a task and that object goes out of scope, the task will
continue to be scheduled. The task will run to completion or until cancelled.
If this is undesirable consider writing a `deinit` method to cancel associated
running tasks. Applications can call `deinit`, for example in a `try...finally`
block or in a context manager.

###### [Contents](./TUTORIAL.md#contents)

# 5 Exceptions timeouts and cancellation

These topics are related: `uasyncio` enables the cancellation of tasks, and the
application of a timeout to a task, by throwing an exception to the task.

## 5.1 Exceptions

Consider a task `foo` created with `asyncio.create_task(foo())`. This task
might `await` other tasks, with potential nesting. If an exception occurs, it
will propagate up the chain until it reaches `foo`. This behaviour is as per
function calls: the exception propagates up the call chain until trapped. If
the exception is not trapped, the `foo` task stops with a traceback. Crucially
other tasks continue to run.

This does not apply to the main task started with `asyncio.run`. If an
exception propagates to that task, the scheduler will stop. This can be
demonstrated as follows:

```python
import uasyncio as asyncio

async def bar():
    await asyncio.sleep(0)
    1/0  # Crash

async def foo():
    await asyncio.sleep(0)
    print('Running bar')
    await bar()
    print('Does not print')  # Because bar() raised an exception

async def main():
    asyncio.create_task(foo())
    for _ in range(5):
        print('Working')  # Carries on after the exception
        await asyncio.sleep(0.5)
    1/0  # Stops the scheduler
    await asyncio.sleep(0)
    print('This never happens')
    await asyncio.sleep(0)

asyncio.run(main())
```
If `main` issued `await foo()` rather than `create_task(foo())` the exception
would propagate to `main`. Being untrapped, the scheduler, and hence the script,
would stop.

#### Warning

Using `throw` or `close` to throw an exception to a task is unwise. It subverts
`uasyncio` by forcing the task to run, and possibly terminate, when it is still
queued for execution.

### 5.1.1 Global exception handler

During development, it is often best if untrapped exceptions stop the program
rather than merely halting a single task. This can be achieved by setting a
global exception handler. This debug aid is not CPython compatible:
```python
import uasyncio as asyncio
import sys

def _handle_exception(loop, context):
    print('Global handler')
    sys.print_exception(context["exception"])
    #loop.stop()
    sys.exit()  # Drastic - loop.stop() does not work when used this way

async def bar():
    await asyncio.sleep(0)
    1/0  # Crash

async def main():
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_handle_exception)
    asyncio.create_task(bar())
    for _ in range(5):
        print('Working')
        await asyncio.sleep(0.5)

asyncio.run(main())
```

### 5.1.2 Keyboard interrupts

There is a "gotcha" illustrated by the following code sample. If allowed to run
to completion, it works as expected.

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

try:
    asyncio.run(bar())
except ZeroDivisionError:
    asyncio.run(shutdown())
except KeyboardInterrupt:
    print('Keyboard interrupt at loop level.')
    asyncio.run(shutdown())
```

However, issuing a keyboard interrupt causes the exception to go to the
outermost scope. This is because `uasyncio.sleep` causes execution to be
transferred to the scheduler. Consequently, applications requiring cleanup code
in response to a keyboard interrupt should trap the exception at the outermost
scope.

###### [Contents](./TUTORIAL.md#contents)

## 5.2 Cancellation and Timeouts

Cancellation and timeouts work by throwing an exception to the task. This is
unlike a normal exception. If a task cancels another, the running task
continues to execute until it yields to the scheduler. Task cancellation occurs
at that point, whether or not the cancelled task is scheduled for execution: a
task waiting on (say) an `Event` or a `sleep` will be cancelled.

For tasks launched with `.create_task` the exception is transparent to the
user: the task simply stops as described above. It is possible to trap the
exception, for example to perform cleanup code, typically in a `finally`
clause. The exception thrown to the task is `uasyncio.CancelledError` in both
cancellation and timeout. There is no way for the task to distinguish between
these two cases.

As stated above, for a task launched with `.create_task`, trapping the error is
optional. Where a task is `await`ed, to avoid a halt it must be trapped within
the task, within the `await`ing scope, or both. In the last case, the task must
re-raise the exception after trapping so that the error can again be trapped in
the outer scope.

## 5.2.1 Task cancellation

The `Task` class has a `cancel` method. This throws a `CancelledError` to the
task. This works with nested tasks. Usage is as follows:
```python
import uasyncio as asyncio
async def printit():
    print('Got here')
    await asyncio.sleep(1)

async def foo():
    while True:
        await printit()
        print('In foo')

async def bar():
    foo_task = asyncio.create_task(foo())  # Create task from task
    await asyncio.sleep(4)  # Show it running
    foo_task.cancel()
    await asyncio.sleep(0)
    print('foo is now cancelled.')
    await asyncio.sleep(4)  # Proof!

asyncio.run(bar())
```
The exception may be trapped as follows:
```python
import uasyncio as asyncio
async def printit():
    print('Got here')
    await asyncio.sleep(1)

async def foo():
    try:
        while True:
            await printit()
    except asyncio.CancelledError:
        print('Trapped cancelled error.')
        raise  # Enable check in outer scope
    finally:  # Usual way to do cleanup
        print('Cancelled - finally')

async def bar():
    foo_task = asyncio.create_task(foo())
    await asyncio.sleep(4)
    foo_task.cancel()
    await asyncio.sleep(0)
    print('Task is now cancelled')
asyncio.run(bar())
```
As of firmware V1.18, the `current_task()` method is supported. This enables a
task to pass itself to other tasks, enabling them to cancel it. It also
facilitates the following pattern:

```python
class Foo:
    async def run(self):
        self.task = asyncio.current_task()
        # code omitted

    def cancel(self):
        self.task.cancel()
```

###### [Contents](./TUTORIAL.md#contents)

## 5.2.2 Tasks with timeouts

Timeouts are implemented by means of `uasyncio` methods `.wait_for()` and
`.wait_for_ms()`. These take as arguments a task and a timeout in seconds or ms
respectively. If the timeout expires, a `uasyncio.CancelledError` is thrown to
the task, while the caller receives a `TimeoutError`. Trapping the exception in
the task is optional. The caller must trap the `TimeoutError`, otherwise the
exception will interrupt program execution.

```python
import uasyncio as asyncio

async def forever():
    try:
        print('Starting')
        while True:
            await asyncio.sleep_ms(300)
            print('Got here')
    except asyncio.CancelledError:  # Task sees CancelledError
        print('Trapped cancelled error.')
        raise
    finally:  # Usual way to do cleanup
        print('forever timed out')

async def foo():
    try:
        await asyncio.wait_for(forever(), 3)
    except asyncio.TimeoutError:  # Mandatory error trapping
        print('foo got timeout')  # Caller sees TimeoutError
    await asyncio.sleep(2)

asyncio.run(foo())
```

## 5.2.3 Cancelling running tasks

This useful technique can provoke counter intuitive behaviour. Consider a task
`foo` created using `create_task`. Then tasks `bar`, `cancel_me` (and possibly
others) are created with code like:
```python
async def bar():
    await foo
    # more code
```
All will pause waiting for `foo` to terminate. If any one of the waiting tasks
is cancelled, the cancellation will propagate to `foo`. This would be expected
behaviour if `foo` were a coro. The fact that it is a running task means that
the cancellation impacts the tasks waiting on it; it actually causes their
cancellation. Again, if `foo` were a coro and a task or coro was waiting on it,
cancelling `foo` would be expected to propagate to the caller. In the context
of running tasks, this may be unwelcome.

The behaviour is "correct": CPython `asyncio` behaves identically. Ref
[this forum thread](https://forum.micropython.org/viewtopic.php?f=2&t=8158).

###### [Contents](./TUTORIAL.md#contents)

# 6 Interfacing hardware

At heart, all interfaces between `uasyncio` and external asynchronous events
rely on polling. This is because of the cooperative nature of `uasyncio`
scheduling: the task which is expected to respond to the event can only acquire
control after another task has relinquished it. There are two ways to handle
this.
 * Implicit polling: when a task yields and the scheduler acquires control, the
 scheduler checks for an event. If it has occurred it schedules a waiting task.
 This is the approach used by `ThreadSafeFlag`.
 * Explicit polling: a user task does busy-wait polling on the hardware.

At its simplest, explicit polling may consist of code like this:
```python
async def poll_my_device():
    global my_flag  # Set by device ISR
    while True:
        if my_flag:
            my_flag = False
            # service the device
        await asyncio.sleep(0)
```

In place of a global, an instance variable or an instance of an awaitable class
might be used. Explicit polling is discussed further
[below](./TUTORIAL.md#62-polling-hardware-with-a-task).

Implicit polling is more efficient and may gain further from planned
improvements to I/O scheduling. Aside from the use of `ThreadSafeFlag`, it is
possible to write code which uses the same technique. This is by designing the
driver to behave like a stream I/O device such as a socket or UART, using
`stream I/O`. This polls devices using Python's `select.poll` system: because
polling is done in C it is faster and more efficient than explicit polling. The
use of `stream I/O` is discussed
[here](./TUTORIAL.md#63-using-the-stream-mechanism).

Owing to its efficiency, implicit polling most benefits fast I/O device drivers:
streaming drivers can be written for many devices not normally considered as
streaming devices [section 6.4](./TUTORIAL.md#64-writing-streaming-device-drivers).

There are hazards involved with approaches to interfacing ISR's which appear to
avoid polling. It is invalid to issue `create_task` or to trigger an `Event` in
an ISR as these can cause a race condition in the scheduler.

###### [Contents](./TUTORIAL.md#contents)

## 6.1 Timing issues

Both explicit and implicit polling are currently based on round-robin
scheduling. Assume I/O is operating concurrently with N user tasks each of
which yields with a zero delay. When I/O has been serviced it will next be
polled once all user tasks have been scheduled. The implied latency needs to be
considered in the design. I/O channels may require buffering, with an ISR
servicing the hardware in real time from buffers and tasks filling or
emptying the buffers in slower time.

The possibility of overrun also needs to be considered: this is the case where
something being polled by a task occurs more than once before the task is
actually scheduled.

Another timing issue is the accuracy of delays. If a task issues

```python
    await asyncio.sleep_ms(t)
    # next line
```

the scheduler guarantees that execution will pause for at least `t`ms. The
actual delay may be greater depending on the system state when `t` expires.
If, at that time, all other tasks are waiting on nonzero delays, the next line
will immediately be scheduled. But if other tasks are pending execution (either
because they issued a zero delay or because their time has also elapsed) they
may be scheduled first. This introduces a timing uncertainty into the `sleep()`
and `sleep_ms()` functions. The worst-case value for this overrun may be
calculated by summing, for every other task, the worst-case execution time
between yielding to the scheduler.

###### [Contents](./TUTORIAL.md#contents)

## 6.2 Polling hardware with a task

This is a simple approach, but is most appropriate to hardware which may be
polled at a relatively low rate. This is primarily because polling with a short
(or zero) polling interval may cause the task to consume more processor time
than is desirable.

The example `apoll.py` demonstrates this approach by polling the Pyboard
accelerometer at 100ms intervals. It performs some simple filtering to ignore
noisy samples and prints a message every two seconds if the board is not moved.

Further examples may be found in the primitives directory, notably `switch.py`
and `pushbutton.py`: drivers for switch and pushbutton devices.

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
        await foo  # Other tasks are scheduled while we wait
        rx_data = foo.read_record()
        print('Got: {}'.format(rx_data))
        await foo.send_record(rx_data)
        rx_data = b''

asyncio.run(run())
```

###### [Contents](./TUTORIAL.md#contents)

## 6.3 Using the stream mechanism

This section applies to platforms other than the Unix build. The latter handles
stream I/O in a different way described
[here](https://github.com/micropython/micropython/issues/7965#issuecomment-960259481).
Code samples may not run under the Unix build until it is made more compatible
with other platforms.

The stream mechanism can be illustrated using a Pyboard UART. This code sample
demonstrates concurrent I/O on one UART. To run, link Pyboard pins X1 and X2
(UART Txd and Rxd).

```python
import uasyncio as asyncio
from machine import UART
uart = UART(4, 9600, timeout=0)  # timeout=0 prevents blocking at low baudrates

async def sender():
    swriter = asyncio.StreamWriter(uart, {})
    while True:
        swriter.write('Hello uart\n')
        await swriter.drain()  # Transmission starts now.
        await asyncio.sleep(2)

async def receiver():
    sreader = asyncio.StreamReader(uart)
    while True:
        res = await sreader.readline()
        print('Received', res)

async def main():
    rx = asyncio.create_task(receiver())
    tx = asyncio.create_task(sender())
    await asyncio.sleep(10)
    print('Quitting')
    tx.cancel()
    rx.cancel()
    await asyncio.sleep(1)
    print('Done')

asyncio.run(main())
```
Writing to a `StreamWriter` occurs in two stages. The synchronous `.write`
method concatenates data for later transmission. The asynchronous `.drain`
causes transmission. To avoid allocation call `.drain` after each call to
`.write`. If multiple tasks are to write to the same `StreamWriter`, the best
solution is to implement a shared `Queue`. Each task writes to the `Queue` and
a single task waits on it, issuing `.write` and `.drain` whenever data is
queued. Do not have multiple tasks calling `.drain` concurrently: this can
result in data corruption for reasons detailed
[here](https://github.com/micropython/micropython/issues/6621).

The mechanism works because the device driver (written in C) implements the
following methods: `ioctl`, `read`, `readline` and `write`. See
[Writing streaming device drivers](./TUTORIAL.md#64-writing-streaming-device-drivers)
for details on how such drivers may be written in Python.

A UART can receive data at any time. The stream I/O mechanism checks for pending
incoming characters whenever the scheduler has control. When a task is running
an interrupt service routine buffers incoming characters; these will be removed
when the task yields to the scheduler. Consequently UART applications should be
designed such that tasks minimise the time between yielding to the scheduler to
avoid buffer overflows and data loss. This can be ameliorated by using a larger
UART read buffer or a lower baudrate. Alternatively hardware flow control will
provide a solution if the data source supports it.

### 6.3.1 A UART driver example

The program [auart_hd.py](../as_demos/auart_hd.py) illustrates a method of
communicating with a half duplex device such as one responding to the modem
'AT' command set. Half duplex means that the device never sends unsolicited
data: its transmissions are always in response to a command from the master.

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
multiple tasks each polling a device, partly because `select` is written in C
but also because the task performing the polling is descheduled until the
`poll` object returns a ready status.

A device driver capable of employing the stream I/O mechanism may support
`StreamReader`, `StreamWriter` instances or both. A readable device must
provide at least one of the following methods. Note that these are synchronous
methods. The `ioctl` method (see below) ensures that they are only called if
data is available. The methods should return as fast as possible with as much
data as is available.

`readline()` Return as many characters as are available up to and including any
newline character. Required if you intend to use `StreamReader.readline()`.
It should return a maximum of one line.  
`read(n)` Return as many characters as are available but no more than `n`.
Required to use `StreamReader.read()` or `StreamReader.readexactly()`  

A writeable driver must provide this synchronous method:  
`write` Arg `buf`: the buffer to write. This can be a `memoryview`.  
It should return immediately. The return value is the number of characters
actually written (may well be 1 if the device is slow). The `ioctl` method
ensures that this is only called if the device is ready to accept data.

Note that this has changed relative to `uasyncio` V2. Formerly `write` had
two additional mandatory args. Existing code will fail because `Stream.drain`
calls `write` with a single arg (which can be a `memoryview`).

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

The following is a complete awaitable delay class.
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
        await self.sreader.read(1)

    def __call__(self, ms):
        self.end = utime.ticks_add(utime.ticks_ms(), ms)
        return self

    def read(self, _):
        return "a"

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                if utime.ticks_diff(utime.ticks_ms(), self.end) >= 0:
                    ret |= MP_STREAM_POLL_RD
        return ret

async def timer_test(n):
    timer = MillisecTimer()
    for x in range(n):
        await timer(100)  # Pause 100ms
        print(x)

asyncio.run(timer_test(20))
```

This currently confers no benefit over `await asyncio.sleep_ms()`, however if
`uasyncio` implements fast I/O scheduling it will be capable of more precise
timing. This is because I/O will be tested on every scheduler call. Currently
it is polled once per complete pass, i.e. when all other pending tasks have run
in round-robin fashion.

It is possible to use I/O scheduling to associate an event with a callback.
This is more efficient than a polling loop because the task doing the polling
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
        asyncio.create_task(self.run())

    async def run(self):
        while True:
            await self.sreader.read(1)

    def read(self, _):
        v = self.pinval
        if v and self.cb_rise is not None:
            self.cb_rise(*self.cbr_args)
            return
        if not v and self.cb_fall is not None:
            self.cb_fall(*self.cbf_args)

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

Once again latency can be high: if implemented fast I/O scheduling will improve
this.

The demo program [iorw.py](./as_demos/iorw.py) illustrates a complete example.

###### [Contents](./TUTORIAL.md#contents)

## 6.5 A complete example: aremote.py

See [aremote.py](../as_drivers/nec_ir/aremote.py) documented
[here](./NEC_IR.md). This is a complete device driver: a receiver/decoder for
an infra red remote controller. The following notes are salient points
regarding its `asyncio` usage.

A pin interrupt records the time of a state change (in μs) and sends a
`Message`, passing the time when the first state change occurred. A task waits
on the `Message`, yields for the duration of a data burst, then decodes the
stored data before calling a user-specified callback.

Passing the time to the `Message` instance enables the task to compensate for
any `asyncio` latency when setting its delay period.

###### [Contents](./TUTORIAL.md#contents)

## 6.6 HTU21D environment sensor

This chip provides accurate measurements of temperature and humidity. The
driver is documented [here](./HTU21D.md). It has a continuously running
task which updates `temperature` and `humidity` bound variables which may be
accessed "instantly".

The chip takes on the order of 120ms to acquire both data items. The driver
works asynchronously by triggering the acquisition and using
`await asyncio.sleep(t)` prior to reading the data. This allows other tasks to
run while acquisition is in progress.

```python
import as_drivers.htu21d.htu_test
```

###### [Contents](./TUTORIAL.md#contents)

# 7 Hints and tips

## 7.1 Program hangs

Hanging usually occurs because a task has blocked without yielding: this will
hang the entire system. When developing, it is useful to have a task which
periodically toggles an onboard LED. This provides confirmation that the
scheduler is running.

## 7.2 uasyncio retains state

If a `uasyncio` application terminates, the state is retained. Embedded code seldom
terminates, but in testing, it is useful to re-run a script without the need for
a soft reset. This may be done as follows:
```python
import uasyncio as asyncio

async def main():
    await asyncio.sleep(5)  # Dummy test script

def test():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # Trapping this is optional
        print('Interrupted')  # or pass
    finally:
        asyncio.new_event_loop()  # Clear retained state
```
It should be noted that clearing retained state is not a panacea. Re-running
complex applications may require the state to be retained.

###### [Contents](./TUTORIAL.md#contents)

## 7.3 Garbage Collection

You may want to consider running a task which issues:

```python
    gc.collect()
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
```

This assumes `import gc` has been issued. The purpose of this is discussed
[here](http://docs.micropython.org/en/latest/reference/constrained.html#the-heap).

###### [Contents](./TUTORIAL.md#contents)

## 7.4 Testing

It's advisable to test that a device driver yields control when you intend it
to. This can be done by running one or more instances of a dummy task which
runs a loop printing a message, and checking that it runs in the periods when
the driver is blocking:

```python
async def rr(n):
    while True:
        print('Roundrobin ', n)
        await asyncio.sleep(0)
```

As an example of the type of hazard which can occur, in the `RecordOrientedUart`
example above, the `__await__` method was originally written as:

```python
    def __await__(self):
        data = b''
        while not data.endswith(self.DELIMITER):
            while not self.uart.any():
                yield from asyncio.sleep(0)
            data = b''.join((data, self.uart.read(self.uart.any())))
        self.data = data
```

In testing, this hogged execution until an entire record was received. This was
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
A coro instance is created and discarded, typically leading to a program
silently failing to run correctly:

```python
import uasyncio as asyncio
async def foo():
    await asyncio.sleep(1)
    print('done')

async def main():
    foo()  # Should read: await foo

asyncio.run(main())
```

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

Support for TLS on nonblocking sockets is platform dependent. It works on ESP32,
Pyboard D and ESP8266.

The use of nonblocking sockets requires some attention to detail. If a
nonblocking read is performed, because of server latency, there is no guarantee
that all (or any) of the requested data is returned. Likewise writes may not
proceed to completion.

Hence asynchronous read and write methods need to iteratively perform the
nonblocking operation until the required data has been read or written. In
practice a timeout is likely to be required to cope with server outages.

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

## 7.7 CPython compatibility and the event loop

The samples in this tutorial are compatible with CPython 3.8. If you need
compatibility with versions 3.5 or above, the `asyncio.run()` method is absent.
Replace:
```python
asyncio.run(my_task())
```
with:
```python
loop = asyncio.get_event_loop()
loop.run_until_complete(my_task())
```
The `create_task` method is a member of the `event_loop` instance. Replace
```python
asyncio.create_task(my_task())
```
with
```python
loop = asyncio.get_event_loop()
loop.create_task(my_task())
```
Event loop methods are supported in `uasyncio` and in CPython 3.8 but are
deprecated. To quote from the official docs:

Application developers should typically use the high-level asyncio functions,
such as `asyncio.run()`, and should rarely need to reference the loop object or
call its methods. This section is intended mostly for authors of lower-level
code, libraries, and frameworks, who need finer control over the event loop
behavior ([reference](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.get_event_loop)).

This doc offers better alternatives to `get_event_loop` if you can confine
support to CPython V3.8+.

There is an event loop method `run_forever` which takes no args and causes the
event loop to run. This is supported by `uasyncio`. This has use cases, notably
when all of an application's tasks are instantiated in other modules.

## 7.8 Race conditions

These occur when coroutines compete for access to a resource, each using the
resource in a mutually incompatible manner.

This behaviour can be demonstrated by running [the switch test](./primitives/tests/switches.py).
In `test_sw()` coroutines are scheduled by events. If the switch is cycled
rapidly the LED behaviour may seem surprising. This is because each time the
switch is closed, a coro is launched to flash the red LED, and on each open event,
a coro is launched for the green LED. With rapid cycling a new coro instance will
commence while one is still running against the same LED. This race condition
leads to the LED behaving erratically.

This is a hazard of asynchronous programming. In some situations, it is
desirable to launch a new instance on each button press or switch closure, even
if other instances are still incomplete. In other cases it can lead to a race
condition, leading to the need to code an interlock to ensure that the desired
behaviour occurs. The programmer must define the desired behaviour.

In the case of this test program it might be to ignore events while a similar
one is running, or to extend the timer to prolong the LED illumination.
Alternatively a subsequent button press might be required to terminate the
illumination. The "right" behaviour is application dependent.

## 7.9 Undocumented uasyncio features

These may be subject to change.

A `Task` instance has a `.done()` method that returns `True` if the task has
terminated (by running to completion, by throwing an exception or by being
cancelled).

If a task has completed, a `.data` bound variable holds any result which was
returned by the task. If the task throws an exception or is cancelled `.data`
holds the exception (or `CancelledError`).

###### [Contents](./TUTORIAL.md#contents)

# 8 Notes for beginners

These notes are intended for those new to asynchronous code. They start by
outlining the problems which schedulers seek to solve, and give an overview of
the `uasyncio` approach to a solution.

[Section 8.5](./TUTORIAL.md#85-why-cooperative-rather-than-pre-emptive)
discusses the relative merits of `uasyncio` and the `_thread` module and why
you may prefer to use cooperative (`uasyncio`) over pre-emptive (`_thread`)
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
        asyncio.create_task(self.run())

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

async def main():
    leds = [LED_async(n) for n in range(1, 4)]
    for n, led in enumerate(leds):
        led.flash(0.7 + n/4)
    sw = pyb.Switch()
    while not sw.value():
        await asyncio.sleep_ms(100)

asyncio.run(main())
```

In contrast to the event loop example the logic associated with the switch is
in a function separate from the LED functionality. Note the code used to start
the scheduler:

```python
asyncio.run(main())  # Execution passes to tasks.
 # It only continues here once main() terminates, when the
 # scheduler has stopped.
```

###### [Contents](./TUTORIAL.md#contents)

## 8.4 Scheduling in uasyncio

Python 3.5 and MicroPython support the notion of an asynchronous function,
known as a task. A task normally includes at least one `await` statement.

```python
async def hello():
    for _ in range(10):
        print('Hello world.')
        await asyncio.sleep(1)
```

This function prints the message ten times at one second intervals. While the
function is paused pending the time delay `asyncio` will schedule other tasks,
providing an illusion of concurrency.

When a task issues `await asyncio.sleep_ms()` or `await asyncio.sleep()` the
current task pauses: it is placed on a queue which is ordered on time due, and
execution passes to the task at the top of the queue. The queue is designed so
that even if the specified sleep is zero other due tasks will run before the
current one is resumed. This is "fair round-robin" scheduling. It is common
practice to issue `await asyncio.sleep(0)` in loops to ensure a task doesn't
hog execution. The following shows a busy-wait loop which waits for another
task to set the global `flag`. Alas it monopolises the CPU preventing other
tasks from running:

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
resume until the running task issues `await` or terminates. A well-behaved task
will always issue `await` at regular intervals. Where a precise delay is
required, especially one below a few ms, it may be necessary to use
`utime.sleep_us(us)`.

###### [Contents](./TUTORIAL.md#contents)

## 8.5 Why cooperative rather than pre-emptive?

The initial reaction of beginners to the idea of cooperative multi-tasking is
often one of disappointment. Surely pre-emptive is better? Why should I have to
explicitly yield control when the Python virtual machine can do it for me?

My background is in hardware interfacing: I am not a web developer. I found
[this video](https://www.youtube.com/watch?v=kdzL3r-yJZY) to be an interesting
beginner-level introduction to asynchronous web programming which discusses the
relative merits of cooperative and pre-emptive scheduling in that environment.

When it comes to embedded systems the cooperative model has two advantages.
Firstly, it is lightweight. It is possible to have large numbers of tasks
because unlike descheduled threads, paused tasks contain little state.
Secondly it avoids some of the subtle problems associated with pre-emptive
scheduling. In practice, cooperative multi-tasking is widely used, notably in
user interface applications.

To make a case for the defence a pre-emptive model has one advantage: if
someone writes

```python
for x in range(1000000):
    # do something time consuming
```

it won't lock out other threads. Under cooperative schedulers, the loop must
explicitly yield control every so many iterations e.g. by putting the code in
a task and periodically issuing `await asyncio.sleep(0)`.

Alas this benefit of pre-emption pales into insignificance compared to the
drawbacks. Some of these are covered in the documentation on writing
[interrupt handlers](http://docs.micropython.org/en/latest/reference/isr_rules.html).
In a pre-emptive model every thread can interrupt every other thread, changing
data which might be used in other threads. It is generally much easier to find
and fix a lockup resulting from a task which fails to yield than locating the
sometimes deeply subtle and rarely occurring bugs which can occur in
pre-emptive code.

To put this in simple terms, if you write a MicroPython task, you can be
sure that variables won't suddenly be changed by another task: your task has
complete control until it issues `await asyncio.sleep(0)`.

Bear in mind that interrupt handlers are pre-emptive. This applies to both hard
and soft interrupts, either of which can occur at any point in your code.

An eloquent discussion of the evils of threading may be found
[in threads are bad](https://glyph.twistedmatrix.com/2014/02/unyielding.html).

###### [Contents](./TUTORIAL.md#contents)

## 8.6 Communication

In non-trivial applications, tasks need to communicate. Conventional Python
techniques can be employed. These include the use of global variables or
declaring tasks as object methods: these can then share instance variables.
Alternatively a mutable object may be passed as a task argument.

Pre-emptive systems mandate specialist classes to achieve "thread safe"
communications; in a cooperative system these are seldom required.

###### [Contents](./TUTORIAL.md#contents)

# 9. Polling vs Interrupts

The role of interrupts in cooperative systems has proved to be a source of
confusion in the forum. The merit of an interrupt service routine (ISR) is that
it runs very soon after the event causing it. On a Pyboard, Python code may be
running 15μs after a hardware change, enabling prompt servicing of hardware and
accurate timing of signals.

The question arises whether it is possible to use interrupts to cause a task to
be scheduled at reduced latency. It is easy to show that, in a cooperative
scheduler, interrupts offer no latency benefit compared to polling the hardware
directly.

The reason for this is that a cooperative scheduler only schedules tasks when
another task has yielded control. Consider a system with a number of concurrent
tasks, where the longest any task blocks before yielding to the scheduler is
`N`ms. In such a system, even with an ideal scheduler, the worst-case latency
between a hardware event occurring and its handling task being scheduled is
`N`ms, assuming that the mechanism for detecting the event adds no latency of
its own.

In practice, `N` is likely to be on the order of many ms. On fast hardware there
will be a negligible performance difference between polling the hardware and
polling a flag set by an ISR. On hardware such as ESP8266 and ESP32 the ISR
approach will probably be slower owing to the long and variable interrupt
latency of these platforms.

Using an ISR to set a flag is probably best reserved for situations where an
ISR is already needed for other reasons.

The above comments refer to an ideal scheduler. Currently `uasyncio` is not in
this category, with worst-case latency being > `N`ms. The conclusions remain
valid.

This, along with other issues, is discussed in 
[Interfacing uasyncio to interrupts](./INTERRUPTS.md).

###### [Contents](./TUTORIAL.md#contents)

# 10. Interfacing threaded code

In the context of a `uasyncio` application, the `_thread` module has two main
uses:
 1. Defining code to run on another core (currently restricted to RP2).
 2. Handling blocking functions. The technique assigns the blocking function to
 another thread. The `uasyncio` system continues to run, with a single task
 paused pending the result of the blocking method.

These techniques, and thread-safe classes to enable their use, are presented in
[this doc](./THREADING.md).

###### [Contents](./TUTORIAL.md#contents)
