# uasyncio: Under the hood

This document aims to explain the operation of `uasyncio` as I understand it. I
did not write the library so the information presented is a result of using it,
studying the code, experiment and inference. There may be errors, in which case
please raise an issue. None of this information is required to use the library:
it is intended to satisfy the curiosity of scheduler geeks or to help those
wishing to modify it.

# 0. Contents

 1. [Introduction](./UNDER_THE_HOOD.md#1-introduction)  
 2. [Generators and coroutines](./UNDER_THE_HOOD.md#2-generators-and-coroutines)  
  2.1 [pend_throw](./UNDER_THE_HOOD.md#21-pend_throw)  
 3. [Coroutine yield types](./UNDER_THE_HOOD.md#3-coroutine-yield-types)  
  3.1 [SysCall1 classes](./UNDER_THE_HOOD.md#31-syscall1-classes)  
 4. [The EventLoop](./UNDER_THE_HOOD.md#4-the-eventloop)  
  4.1 [Exceptions](./UNDER_THE_HOOD.md#41-exceptions)  
  4.2 [Task Cancellation and Timeouts](./UNDER_THE_HOOD.md#42-task-cancellation-and-timeouts)  
 5. [Stream I/O](./UNDER_THE_HOOD.md#5-stream-io)  
  5.1 [StreamReader](./UNDER_THE_HOOD.md#51-streamreader)  
  5.2 [StreamWriter](./UNDER_THE_HOOD.md#52-streamwriter)  
  5.3 [PollEventLoop wait method](./UNDER_THE_HOOD.md#53-polleventloop-wait-method)  
 6. [Modifying uasyncio](./UNDER_THE_HOOD.md#6-modifying-uasyncio)  
 7. [Links](./UNDER_THE_HOOD.md#7-links)

# 1. Introduction

Where the versions differ, this explanation relates to the `fast_io` version.
Note that the code in `fast_io` contains additional comments to explain its
operation. The code the `fast_io` directory is also in
[my micropython-lib fork](https://github.com/peterhinch/micropython-lib.git),
`uasyncio-io-fast-and-rw` branch.

This doc assumes a good appreciation of the use of `uasyncio`. An understanding
of Python generators is also essential, in particular the use of `yield from`
and an appreciation of the difference between a generator and a generator
function:

```python
def gen_func(n):  # gen_func is a generator function
    while True:
        yield n
        n += 1

my_gen = gen_func(7)  # my_gen is a generator
```

The code for the `fast_io` variant of `uasyncio` may be found in:

```
fast_io/__init__.py
fast_io/core.py
```

This has additional code comments to aid in its understanding.

###### [Main README](./README.md)

# 2. Generators and coroutines

In MicroPython coroutines and generators are identical: this differs from
CPython. The knowledge that a coro is a generator is crucial to understanding
`uasyncio`'s operation. Consider this code fragment:

```python
async def bar():
    await asyncio.sleep(1)

async def foo():
    await bar()
```

In MicroPython the `async def` syntax allows a generator function to lack a
`yield` statement. Thus `bar` is a generator function, hence `bar()` returns a
generator.

The `await bar()` syntax is equivalent to `yield from bar()`. So transferring
execution to the generator instantiated by `bar()` does not involve the
scheduler. `asyncio.sleep` is a generator function so `await asyncio.sleep(1)`
creates a generator and transfers execution to it via `yield from`. The
generator yields a value of 1000; this is passed to the scheduler to invoke the
delay by placing the coro onto a `timeq` (see below).

## 2.1 pend_throw

Generators in MicroPython have a nonstandard method `pend_throw`. The Python
`throw` method causes the generator immediately to run and to handle the passed
exception. `pend_throw` retains the exception until the generator (coroutine)
is next scheduled, when the exception is raised. In `fast_io` the task
cancellation and timeout mechanisms aim to ensure that the task is scheduled as
soon as possible to minimise latency.

The `pend_throw` method serves a secondary purpose in `uasyncio`: to store
state in a coro which is paused pending execution. This works because the
object returned from `pend_throw` is that which was previously passed to it, or
`None` on the first call.

```python
a = my_coro.pend_throw(42)
b = my_coro.pend_throw(None)  # Coro can now safely be executed
```
In the above instance `a` will be `None` if it was the first call to
`pend_throw` and `b` will be 42. This is used to determine if a paused task is
on a `timeq` or waiting on I/O. A task on a `timeq` will have an integer value,
being the `ID` of the task; one pending I/O will have `False`.

If a coro is actually run, the only acceptable stored values are `None` or an
exception. The error "exception must be derived from base exception" indicates
an error in the scheduler whereby this constraint has not been satisfied.

###### [Contents](./UNDER_THE_HOOD.md#0-contents)

# 3. Coroutine yield types

Because coroutines are generators it is valid to issue `yield` in a coroutine,
behaviour which would cause a syntax error in CPython. While explicitly issuing
`yield` in a user application is best avoided for CPython compatibility, it is
used internally in `uasyncio`. Further, because `await` is equivalent to
`yield from`, the behaviour of the scheduler in response to `yield` is crucial
to understanding its operation.

Where a coroutine (perhaps at the end of a `yield from` chain) executes

```python
yield some_object
```

the scheduler regains execution. This is because the scheduler passed execution
to the user coroutine with

```python
ret = next(cb)
```

so `ret` contains the object yielded. Subsequent scheduler behaviour depends on
the type of that object. The following object types are handled:

 * `None` The coro is rescheduled and will run in round-robin fashion.  
 Hence `yield` is functionally equivalent to `await asyncio.sleep(0)`.
 * An integer `N`: equivalent to `await asyncio.sleep_ms(N)`.
 * `False` The coro terminates and is not rescheduled.
 * A coro/generator: the yielded coro is scheduled. The coro which issued the
 `yield` is rescheduled.
 * A `SysCall1` instance. See below.

## 3.1 SysCall1 classes

The `SysCall1` constructor takes a single argument stored in `self.arg`. It is
effectively an abstract base class: only subclasses are instantiated. When a
coro yields a `SysCall1` instance, the scheduler's behaviour is determined by
the type of the object and the contents of its `.arg`.

The following subclasses exist:

 * `SleepMs` `.arg` holds the delay in ms. Effectively a singleton with the
 instance in `sleep_ms`. Its `.__call__` enables `await asyncio.sleep_ms(n)`.
 * `StopLoop` Stops the scheduler. `.arg` is returned to the caller.
 * `IORead` Causes an interface to be polled for data ready. `.arg` is the
 interface.
 * `IOWrite` Causes an interface to be polled for ready to accept data. `.arg`
 is the interface.
 * `IOReadDone` These stop polling of an interface (in `.arg`).
 * `IOWriteDone`

The `IO*` classes are for the exclusive use of `StreamReader` and `StreamWriter`
objects.

###### [Contents](./UNDER_THE_HOOD.md#0-contents)

# 4. The EventLoop

The file `core.py` defines an `EventLoop` class which is subclassed by
`PollEventLoop` in `__init__.py`. The latter extends the base class to support
stream I/O. In particular `.wait()` is overridden in the subclass.

The `fast_io` `EventLoop` maintains four queues, `.runq`, `.waitq`, `.lpq` and
`.ioq`. The latter two are only instantiated if specified to the
`get_event_loop` method. Official `uasyncio` does not have `.lpq` or `.ioq`.

Tasks are appended to the bottom of the run queue and retrieved from the top;
in other words it is a First In First Out (FIFO) queue. The I/O queue is
similar. Tasks on `.waitq` and `.lpq` are sorted in order of the time when they
are to run, the task having the soonest time to run at the top.

When a task issues `await asyncio.sleep(t)` or `await asyncio.sleep_ms(t)` and
t > 0 the task is placed on the wait queue. If t == 0 it is placed on the run
queue (by `.call_soon()`). Callbacks are placed on the queues in a similar way
to tasks.

The following is a somewhat broad-brush explanation of an iteration of the
event loop's `run_forever()` method intended to aid in following the code.

The method first checks the wait queue. Any tasks which have become due (or
overdue) are removed and placed on the run queue.

The run queue is then processed. The number of tasks on it is determined: only
that number of tasks will be run. Because the run queue is FIFO this guarantees
that exactly those tasks which were on the queue at the start of processing
this queue will run (even when tasks are appended).

The topmost task/callback is removed and run. If it is a callback the loop
iterates to the next entry. If it is a task, it runs then either yields or
raises an exception. If it yields, the return type is examined as described
above. If the task yields with a zero delay it will be appended to the run
queue, but as described above it will not be rescheduled in this pass through
the queue. If it yields a nonzero delay it will be added to `.waitq` (it has
already been removed from `.runq`).

Once every task which was initially on the run queue has been scheduled, the
queue may or may not be empty depending on whether tasks yielded a zero delay.

At the end of the outer loop a `delay` value is determined. This will be zero
if the run queue is not empty: tasks are ready for scheduling. If the run queue
is empty `delay` is determined from the time to run of the topmost (most
current) task on the wait queue.

The `.wait()` method is called with this delay. If the delay is > 0 the
scheduler pauses for this period (polling I/O). On a zero delay I/O is checked
once: if nothing is pending it returns quickly.

###### [Contents](./UNDER_THE_HOOD.md#0-contents)

## 4.1 Exceptions

There are two "normal" cases where tasks raise an exception: when the task is
complete (`StopIteration`) and when it is cancelled (`CancelledError`). In both
these cases the exception is trapped and the loop proceeds to the next item on
the run queue - the task is simply not rescheduled.

If an unhandled exception occurs in a task this will be propagated to the
caller of `run_forever()` or `run_until_complete` a explained in the tutorial.

## 4.2 Task Cancellation and Timeouts

The `cancel` function uses `pend_throw` to pass a `CancelledError` to the coro
to be cancelled. The generator's `.throw` and `.close` methods cause the coro
to execute code immediately. This is incorrect behaviour for a de-scheduled
coro. The `.pend_throw` method causes the exception to be processed the next
time the coro is scheduled.

In the `fast_io` version the `cancel` function puts the task onto `.runq` or
`.ioq` for "immediate" excecution. In the case where the task is on `.waitq` or
`.lpq` the task ID is added to a `set` `.canned`. When the task reaches the top
of the timeq it is ignored and removed from `.canned`. This Python approach is
less efficient than that in the Paul Sokolovsky fork, but his approach uses a
special version of the C `utimeq` object and so requires his firmware.

Timeouts use a similar mechanism.

###### [Contents](./UNDER_THE_HOOD.md#0-contents)

# 5. Stream IO

Stream I/O is an efficient way of polling stream devices using `select.poll`.
Device drivers for this mechanism must provide an `ioctl` method which reports
whether a read device has data ready, or whether a write device is capable of
accepting data. Stream I/O is handled via `StreamReader` and `StreamWriter`
instances (defined in `__init__.py`).

## 5.1 StreamReader

The class supports three read coros which work in a similar fashion. The coro
yields an `IORead` instance with the device to be polled as its arg. It is
rescheduled when `ioctl` has reported that some data is available. The coro
reads the device by calling the device driver's `read` or `readline` method.
If all available data has been read, the device's read methods must update the
status returned by its `ioctl` method.

The `StreamReader` read coros iterate until the required data has been read,
when the coro yields `IOReadDone(object_to_poll)` before returning the data. If
during this process, `ioctl` reports that no data is available, the coro
yields `IORead(object_to_poll)`. This causes the coro to be descheduled until
data is again available.

The mechanism which causes it to be rescheduled is discussed below (`.wait()`).

When `IORead(object_to_poll)` is yielded the `EventLoop` calls `.add_reader()`.
This registers the device with `select.poll` as a reader, and saves the coro
for later rescheduling.

The `PollEventLoop` maintains three dictionaries indexed by the `id` of the
object being polled. These are:

 * `rdobjmap` Value: the suspended read coro.
 * `wrobjmap` Value: the suspended write coro (read and write coros may both be
 in a suspended state).
 * `flags` Value: bitmap of current poll flags.

The `add_reader` method saves the coro in `.rdobjmap` and updates `.flags` and
the poll flags so that `ioctl` will respond to a `MP_STREAM_POLL_RD` query.

When the `StreamReader` read method completes it yields
`IOReadDone(object_to_poll)`: this updates `.flags` and the poll flags so that
`ioctl` no longer responds to an `MP_STREAM_POLL_RD` query.

## 5.2 StreamWriter

This supports the `awrite` coro which works in a similar way to `StreamReader`,
yielding `IOWrite(object_to_poll)` until all data has been written, followed
by `IOWriteDone(object_to_poll)`. 

The mechanism is the same as for reading, except that when `ioctl` returns a
"ready" state for a writeable device it means the device is capable of writing
at least one character.

## 5.3 PollEventLoop wait method

When this is called the `Poll` instance is checked in a one-shot mode. In this
mode it will return either when `delay` has elapsed or when at least one device
is ready.

The poller's `ipoll` method uses the iterator protocol to return successive
`(sock, ev)` tuples where `sock` is the device driver and `ev` is a bitmap of
read and write ready status for that device. The `.wait` method iterates
through each device requiring service.

If the read bit is set (i.e. `ioctl` reported data available) the read coro is
retrieved from `.rdobjmap` and queued for scheduling. This is done via
`._call_io`: this puts the coro onto `.runq` or `.ioq` depending on whether an
I/O queue has been instantiated.

Writing is handled similarly.

###### [Contents](./UNDER_THE_HOOD.md#0-contents)

# 6. Modifying uasyncio

The library is designed to be extensible. By following these guidelines a
module can be constructed which alters the functionality of asyncio without the
need to change the official library. Such a module may be used where `uasyncio`
is implemented as frozen bytecode as in official release binaries.

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

###### [Contents](./UNDER_THE_HOOD.md#0-contents)

# 7. Links

Initial discussion of priority I/O scheduling [here](https://github.com/micropython/micropython/issues/2664).  

MicroPython PR enabling stream device drivers to be written in Python 
[PR #3836: io.IOBase](https://github.com/micropython/micropython/pull/3836).
Includes discussion of the read/write bug.  

My outstanding uasyncio PR's: fast I/O
[PR #287](https://github.com/micropython/micropython-lib/pull/287) improved
error reporting 
[PR #292](https://github.com/micropython/micropython-lib/pull/292).

This caught my attention for usefulness and compliance with CPython:
[PR #270](https://github.com/micropython/micropython-lib/pull/270).

###### [Main README](./README.md)
