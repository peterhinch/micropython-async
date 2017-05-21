# Use of MicroPython uasyncio library

This GitHub repository consists of the following parts:
 * [Asynchronous device drivers](./DRIVERS.md). A module providing drivers for
 devices such as switches and pushbuttons.
 * [Synchronisation primitives](./PRIMITIVES.md).
 * [A tutorial](./TUTORIAL.md) An introductory tutorial on asynchronous
 programming and the use of the uasyncio library is offered. This is a work in
 progress, not least because uasyncio is not yet complete.
 * [A driver for an IR remote control](./nec_ir/README.md) This is intended as
 an example of an asynchronous device driver. It decodes signals received from
 infra red remote controls using the popular NEC protocol.
 * [A modified uasyncio](./FASTPOLL.md) This incorporates a simple priority
 mechanism. With suitable application design this improves the rate at which
 devices can be polled and improves the accuracy of time delays.

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

 * Event loop method ``call_later_ms``
 * uasyncio ``sleep_ms(time)``

It doesn't support objects of type ``Future`` and ``Task``. Routines to run
concurrently are defined as coroutines instantiated with ``async def`` and
yield execution with ``await <awaitable>``.

## Asynchronous I/O and uselect

At the time of writing this was under development. Asynchronous I/O works with
devices whose drivers support streaming, such as the UART. As I understand it
support for ``select`` is in the pipeline. Check the current state on GitHub.

## Time values

For timing asyncio uses floating point values of seconds. The uasyncio ``sleep``
method accepts floats (including sub-second values) or integers. Note that in
MicroPython the use of floats implies RAM allocation which incurs a performance
penalty. The design of uasyncio enables allocation-free scheduling. In
applications where performance is an issue, integers should be used and the
millisecond level functions (with integer arguments) employed where necessary.

The ``loop.time`` method returns an integer number of milliseconds whereas
CPython returns a floating point number of seconds. ``call_at`` follows the
same convention.
