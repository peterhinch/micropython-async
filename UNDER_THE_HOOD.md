# uasyncio: Under the hood

This document aims to explain the operation of `uasyncio` as I understand it. I
did not write the library so the information presented is a result of using it,
also studying the code, experiment and inference. There may be errors, in which
case please raise an issue. None of the information here is required to use the
library.

It assumes a good appreciation of the use of `uasyncio`. Familiarity with
Python generators is also recommended, in particular the use of `yield from`
and appreciating the difference between a generator and a generator function:

```python
def gen_func(n):  # gen_func is a generator function
    while True:
        yield n
        n += 1

my_gen = gen_func(7)  # my_gen is a generator
```

The code for `uasyncio` may be found in micropython-lib in the following
directories:

```
uasyncio/uasyncio/__init__.py
uasyncio.core/uasyncio/core.py
```

# Generators and coroutines

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
delay (see below).

# Coroutine yield types

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
 Hence `yield` is functionally equivalent to `await asyncio.sleep(0)`
 * An integer `N`: equivalent to `await asyncio.sleep_ms(N)`.
 * `False` The coro terminates and is not rescheduled.
 * A coro/generator: the yielded coro is scheduled. The coro which issued the
 `yield` is rescheduled.
 * A `SysCall1` instance. See below.

## SysCall1 classes

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
 * `IOReadDone` These stop polling of an interface.
 * `IOWriteDone`

The `IO*` classes are for the exclusive use of `StreamReader` and `StreamWriter`
objects.

# The EventLoop

The file `core.py` defines an `EventLoop` class which is subclassed by
`PollEventLoop` in `__init__.py`. The latter extends the base class to support
stream I/O. In particular `.wait()` is overridden in the subclass.

The `EventLoop` maintains two queues, `.runq` and `.waitq`. Tasks are appended
to the bottom of the run queue and retrieved from the top; in other words it is
a First In First Out (FIFO) queue. Tasks on the wait queue are sorted in order
of the time when they are to run, the task having the soonest time to run at
the top.

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
raises an exception. If it yields the return type is examined as described
above. If the task yields with a zero delay it will be appended to the run
queue, but as described above it will not be rescheduled in this pass through
the queue.

Once every task which was initially on the run queue has been scheduled, the
queue may or may not be empty depending on whether tasks yielded a zero delay.

At the end of the outer loop a `delay` value is determined. This will be zero
if the run queue is not empty: tasks are ready for scheduling. If the run queue
is empty `delay` is determined from the time to run of the topmost (most
current) task on the wait queue.

The `.wait()` method is called with this delay. If the delay is > 0 the
scheduler pauses for this period (polling I/O). On a zero delay I/O is checked
once: if nothing is pending it returns quickly.

## Exceptions

There are two "normal" cases where tasks raise an exception: when the task is
complete (`StopIteration`) and when it is cancelled (`CancelledError`). In both
these cases the exception is trapped and the loop proceeds to the next item on
the run queue - the task is simply not rescheduled.

If an unhandled exception occurs in a task this will be propagated to the
caller of `run_forever()` or `run_until_complete` a explained in the tutorial.

# Stream I/O

This description of stream I/O is based on my code rather than the official
version.

Stream I/O is an efficient way of polling stream devices using `select.poll`.
Device drivers for this mechanism must provide an `ioctl` method which reports
whether a read device has data ready, or whether a write device is capable of
accepting data. Stream I/O is handled via `StreamReader` and `StreamWriter`
instances (defined in `__init__.py`).

## StreamReader

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

## StreamWriter

This supports the `awrite` coro which works in a similar way to `StreamReader`,
yielding `IOWrite(object_to_poll)` until all data has been written, followed
by `IOWriteDone(object_to_poll)`. 

The mechanism is the same as for reading, except that when `ioctl` returns a
"ready" state for a writeable device it means the device is capable of writing
at least one character.

## PollEventLoop.wait()

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
