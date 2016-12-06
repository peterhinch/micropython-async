# Application of uasyncio to hardware interfaces

The MicroPython uasyncio library comprises a subset of Python's asyncio library
designed for use on microcontrollers. As such it has a small RAM footprint and
fast context switching. This document describes its use in interfacing hardware
devices and provides classes to support devices including switches and
pushbuttons.

# 1. Installation

This can be done by installing the Unix build of MicroPython, then installing
``uasyncio`` by following the instructions [here](https://github.com/micropython/micropython-lib).
This will create a directory under ``~/.micropython/lib`` which may be copied to
the Pyboard, either to the root or to a ``lib`` subdirectory.

# 2. Introduction

The asyncio concept is of cooperative multi-tasking based on coroutines,
referred in this document as coros.

A key difference between uasyncio and asyncio is that the latter uses floating
point values of seconds for timing. For performance reasons, and to support
ports lacking floating point, uasyncio uses integers. These can refer to seconds
or milliseconds depending on context.

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

loop.call_soon(bar()) # Schedule ASAP
loop.run_forever()
```

Program execution proceeds normally until the call to ``loop.run_forever``. At
this point execution is controlled by the scheduler. A line after
``loop.run_forever`` would never be executed. The scheduler runs ``bar``
because this has been placed on the queue by ``loop.call_soon``. In this
trivial example there is only one coro: ``bar``. If there were others, the
scheduler would schedule them in periods when ``bar`` was paused.

Many embedded applications have an event loop which runs continuously. The event
loop can also be started in a way which permits termination, by using the event
loop's ``run_until_complete`` method. Examples of this may be found in the
``astests.py`` module.

## 2.2 Coroutines (coros)

A coro is instantiated as follows:

```python
async def foo(delay_secs):
    await asyncio.sleep(delay_secs)
    print('Hello')
```

A coro must include at least one of the following statements:

 * ``yield`` Allow the scheduler to schedule another coro.
 * ``yield from mycoro`` Calling coro pauses until mycoro runs to completion.
 * ``await mycoro`` Calling coro pauses until mycoro runs to completion.

A coro is queued for scheduling by means of event loop methods ``call_soon``,
``call_later``, or``call_at``:

```python
loop = asyncio.get_event_loop()
loop.call_soon(foo(5)) # Schedule coro 'foo' ASAP
loop.call_later(2, foo(5)) # Schedule after 2 seconds
loop.call_at(time.ticks_add(loop.time(), 100), foo(2)) # after 100ms
loop.run_forever()
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
the appropriate time has yielded.

More precise delays may be issued by using the ``utime.sleep`` functions. These
are best suited for short delays as the scheduler will be unable to schedule
other coros while the delay is in progress.

# 3. Module aswitch.py

This module provides the following classes:

 * Switch This supports debouncing a normally open switch connected between a
 pin and ground. Can schedule coros on contact closure and/or opening.
 * Pushbutton A generalisation of the Switch to support normally open or
 normally closed switches connected to ground or 3V3. Can also schedule
 coros on double-click or long press events.
 * Delay_ms A class providing a retriggerable delay measured in ms. Can be used
 to schedule a coro. Alternatively its state can be tested by other
 coros.

## 3.1 Switch class

This assumes a normally open switch connected between a pin and ground. The pin
should be initialised as an input with a pullup.

Constructor arguments (defaults in brackets)

 1. ``loop`` The event loop. (Mandatory).
 2. ``pin`` The initialised Pin instance. (Mandatory).
 3. ``close_func`` A coro to be scheduled on switch closure (``None``).
 4. ``close_func_args`` A tuple of arguments for the above (``()``).
 5. ``open_func`` A coro to be scheduled on switch opening (``None``).
 6. ``open_func_args`` A tuple of arguments for the above  (``()``).

The first argument to the open and close coros will be the event loop
instance. This will be followed by any arguments provided in the tuple.

A ``Switch`` object supports one method:
 1. ``__call__`` Call syntax e.g. ``myswitch()`` returns the physical debounced
 state of the switch i.e. 0 if grounded, 1 if connected to ``3V3``.

## 3.2 Pushbutton class

This can support normally open or normally closed switches, connected to ``gnd``
(with a pullup) or to ``3V3`` (with a pull-down). The ``Pin`` object should be
initialised appropriately. The assumption is that on initialisation the button
is not pressed.

The Pushbutton class uses logical rather than physical state: a button's state
is considered ``True`` if pressed, otherwise ``False`` regardless of its
physical implementation.

The pushbutton constructor takes the following arguments (defaults in brackets):

 1. ``loop`` The event loop. (Mandatory).
 2. ``pin`` The initialised Pin instance. (Mandatory).
 3. ``true_func`` A coro to be scheduled on button press (``None``).
 4. ``true_func_args`` Tuple of arguments for above (``()``).
 5. ``false_func`` Coro to be scheduled on button release (``None``).
 6. ``false_func_args`` Tuple of arguments for above (``()``).
 7. ``long_func`` Coro to be scheduled on long press (``None``).
 8. ``long_func_args`` Tuple of arguments for above (``()``).
 9. ``double_func`` Coro to be scheduled on double click (``None``).
 10. ``double_func_args`` Tuple of arguments for above (``()``).

A ``Pushbutton`` object supports two methods.
 1. ``__call__`` Call syntax e.g. ``mybutton()`` returns the logical debounced
 state of the button.
 2. ``rawstate()`` Returns the logical instantaneous state of the button.

## 3.3 Delay_ms class

This implements the software equivalent of a retriggerable monostable or a
watchdog timer. It has a boolean ``running`` state. When instantiated it does
nothing, with ``running`` ``False`` until triggered, when ``running`` becomes
``True``. A timer is then initiated. This can be prevented from timing out by
triggering it again (with a new timeout duration). So long as it is triggered
before the time specified in the preceeding trigger it will never time out.

If it does time out the ``running`` state will revert to ``False``. This can be
interrogated by the object's ``running()`` method. In addition a coro can be
specified to the constructor. This will be scheduled for execution when a
timeout occurs.

Constructor arguments (defaults in brackets):

 1. ``loop``  The event loop. (Mandatory).
 2. ``callback`` The coro to run on timeout (default ``None``).
 3. ``callback_args`` A tuple of arguments for the coro (default ``()``).

User methods:

 1. ``trigger`` argument ``duration``. (Mandatory). A timeout will occur after
 ``duration`` ms unless retriggered.
 2. ``stop`` No argument. Cancels the callback. The timer can be restarted by
 issuing ``trigger`` again.
 3. ``running`` No argument. Returns the running status of the object.

