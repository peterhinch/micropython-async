# Application of uasyncio to hardware interfaces

This document is a "work in progress" as I learn the content myself and
will be subject to substantial revision. At this juncture it will contain
errors.

The MicroPython uasyncio library comprises a subset of Python's asyncio library
designed for use on microcontrollers. As such it has a small RAM footprint and
fast context switching. This document describes its use in interfacing hardware
devices.

# 1. Installation of uasyncio

This can be done by installing the Unix build of MicroPython, then installing
``uasyncio`` by following the instructions [here](https://github.com/micropython/micropython-lib).
This will create a directory under ``~/.micropython/lib`` which may be copied to
the target hardware, either to the root or to a ``lib`` subdirectory.
Alternatively mount the device and use the "-p" option to upip to specify the
target directory as the mounted filesystem.

Another approach is to use CPython's pip to install the files to a local
directory and then copy them to the target.

# 2. Introduction

The asyncio concept is of cooperative multi-tasking based on coroutines,
referred in this document as coros.

## 2.1 Differences from CPython

CPython refers to Python 3.5 as installed on PC's. In the interests of small
size and efficiency uasyncio is a subset of asyncio with some differences.

It doesn't support objects of type ``Future`` and ``Task``. Routines to run
concurrently are defined as coroutines instantiated with ``async def``.

The __await__ special method (to create an awaitable class) is not supported.

For timing asyncio uses floating point values of seconds. For performance
reasons, and to support ports lacking floating point, uasyncio uses integers.
These can refer to seconds or milliseconds depending on context.

## 2.2 Program structure: the event loop

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
because this has been placed on the queue by ``loop.create_task``. In this
trivial example there is only one coro: ``bar``. If there were others, the
scheduler would schedule them in periods when ``bar`` was paused.

Many embedded applications have an event loop which runs continuously. The event
loop can also be started in a way which permits termination, by using the event
loop's ``run_until_complete`` method. Examples of this may be found in the
``astests.py`` module.

The event loop instance is a singleton. If a coro needs to call an event loop
method, calling ``asyncio.get_event_loop()`` will efficiently return it.

## 2.3 Coroutines (coros)

A coro is instantiated as follows:

```python
async def foo(delay_secs):
    await asyncio.sleep(delay_secs)
    print('Hello')
```

A coro can allow other coroutines to run by means of the following statements:

 * ``await mycoro`` Calling coro pauses until mycoro runs to completion, for
 example ``await asyncio.sleep(delay_secs)``.
 * ``yield`` (not allowed in Cpython) arg (optional) a delay in ms. If no delay
 is specified the coro will be rescheduled when other pending coros have run. **TODO** Check this 

### Queueing a coro for scheduling

 * ``EventLoop.create_task`` Arg: the coro to run. Starts the coro ASAP and
 returns immediately.
 * ``await``  Arg: the coro to run. Starts the coro ASAP and waits until it has
 run to completion.

### Running a callback function

Callbacks should be designed to complete in a short period of time to give
coroutines an opportunity to run.

The following ``EventLoop`` methods schedule callbacks:

 1. ``call_soon`` Call as soon as possible. Args: ``callback`` the callback to
 run, ``*args`` any positional args.
 2. ``call_later`` Call after a delay in secs. Args: ``delay``, ``callback``,
 ``*args``
 3. ``call_later_ms_`` Call after a delay in ms. Args: ``delay``, ``callback``,
 ``args``. Args are stored in a tuple for efficiency. Default ``()``
 4. ``call_at`` Call at a future time in secs. Args: ``time``, ``*args``
 5. ``call_at_`` Call at a future time in secs. Args: ``time``, ``args``. Args
 are stored in a tuple for efficiency. Default ``()``

```python
loop = asyncio.get_event_loop()
loop.call_soon(foo(5)) # Schedule callback 'foo' ASAP
loop.call_later(2, foo(5)) # Schedule after 2 seconds
loop.call_at(time.ticks_add(loop.time(), 100), foo(2)) # after 100ms
loop.run_forever()
```

### Returning values

A coro can contain a ``return`` statement with arbitrary return values. To
retrieve them issue:

```python
result = await my_coro()
```

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
the appropriate time has yielded. The amount of uncertainty depends on the
design of the application, but is likely to be on the order of tens of ms.

More precise delays may be issued by using the ``utime.sleep`` functions. These
are best suited for short delays as the scheduler will be unable to schedule
other coros while the delay is in progress.


