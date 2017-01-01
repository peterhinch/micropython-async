# Use of MicroPython uasyncio library

This GitHub repository consists of the following parts:
 * Drivers for hardware documented [here](./DRIVERS.md).
 * Synchronisation primitives described [here](./PRIMITIVES.md).
 * An introductory tutorial on asynchronous programming and the use of the
 uasyncio library is offered [here](./TUTORIAL.md). This is a work in progress,
 not least because uasyncio is not yet complete.

# Installation of uasyncio

Firstly install the latest version of ``micropython-uasyncio``. To use queues, also
install the ``micropython-uasyncio.queues`` module.

Instructions on installing library modules may be found [here](https://github.com/micropython/micropython-lib).

On networked hardware, upip may be run locally.

On non-networked hardware the resultant modules will need to be copied to the
target. The above Unix installation will create directories under
``~/.micropython/lib`` which may be copied to the target hardware, either to
the root or to a ``lib`` subdirectory. Alternatively the device may be mounted;
then use the "-p" option to upip to specify the target directory as the mounted
filesystem.

# Current development state

For those familiar with asyncio under CPython 3.5, uasyncio supports the
following Python 3.5 features:

 * ``async def`` and ``await`` syntax.
 * Awaitable classes (using ``__iter__`` rather than ``__await__``).
 * Asynchronous context managers.
 * Asynchronous iterators.
 * Event loop methods ``call_soon`` and ``call_later``.
 * uasyncio ``sleep(seconds)``.

It supports millisecond level timing with the following:

 * Event loop method ``call_later_ms_``
 * Event loop ``call_at`` - time is specified in ms.
 * uasyncio ``sleep_ms(time)``

It doesn't support objects of type ``Future`` and ``Task``. Routines to run
concurrently are defined as coroutines instantiated with ``async def`` and
yield execution with ``await <awaitable>``.

## Asynchronous I/O and uselect

At the time of writing this was under development. Check the current state on
GitHub.

## Time values

For timing asyncio uses floating point values of seconds. The uasyncio ``sleep``
method accepts floats (including sub-second values) or integers. Note that in
MicroPython the use of floats implies RAM allocation which incurs a performance
penalty. uasyncio is designed to be capable of allocation-free scheduling. In
applications where performance is an issue, integers should be used and the
millisecond level functions (with integer argumnts) employed where necessary.

The ``loop.time`` method returns an integer number of milliseconds whereas
CPython returns a floating point number of seconds. ``call_at`` follows the
same convention.
