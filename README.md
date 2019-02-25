# 1. Asynchronous programming in MicroPython

CPython supports asynchronous programming via the `asyncio` library.
MicroPython provides `uasyncio` which is a subset of this, optimised for small
code size and high performance on bare metal targets. This repository provides
documentation, tutorial material and code to aid in its effective use. It also
contains an optional `fast_io` variant of `uasyncio`.

## The fast_io variant

This comprises two parts.  
 1. The [fast_io](./FASTPOLL.md) version of `uasyncio` is a "drop in"
 replacement for the official version providing bug fixes, additional
 functionality and, in certain respects, higher performance.
 2. An optional extension module enabling the [fast_io](./FASTPOLL.md) version
 to run with very low power draw.

## Resources for users of all versions

 * [A tutorial](./TUTORIAL.md) An introductory tutorial on asynchronous
 programming and the use of the `uasyncio` library.
 * [Asynchronous device drivers](./DRIVERS.md). A module providing drivers for
 devices such as switches and pushbuttons.
 * [Synchronisation primitives](./PRIMITIVES.md). Provides commonly used
 synchronisation primitives plus an API for task cancellation and monitoring.
 * [A driver for an IR remote control](./nec_ir/README.md) This is intended as
 an example of an asynchronous device driver. It decodes signals received from
 infra red remote controls using the popular NEC protocol.
 * [A driver for the HTU21D](./htu21d/README.md) temperature and humidity
 sensor. This is intended to be portable across platforms and is another
 example of an asynchronous device driver.
 * [A driver for character LCD displays](./HD44780/README.md). A simple
 asynchronous interface to displays based on the Hitachi HD44780 chip.
 * [A driver for GPS modules](./gps/README.md) Runs a background task to read
 and decode NMEA sentences, providing constantly updated position, course,
 altitude and time/date information.
 * [Communication using I2C slave mode.](./i2c/README.md) Enables a Pyboard to
 to communicate with another MicroPython device using stream I/O. The Pyboard
 achieves bidirectional communication with targets such as an ESP8266.
 * [Communication between devices](./syncom_as/README.md) Enables MicroPython
 boards to communicate without using a UART. This is hardware agnostic but
 slower than the I2C version.
 * [Under the hood](./UNDER_THE_HOOD.md) A guide to help understand the
 `uasyncio` code. For scheduler geeks and those wishing to modify `uasyncio`.
 
# 2. Version and installation of uasyncio

Paul Sokolovsky (`uasyncio` author) has released `uasyncio` V2.2.1. This version
is on PyPi and requires his [Pycopy](https://github.com/pfalcon/micropython)
fork of MicroPython firmware. His `uasyncio` code may also be found in
[his fork of micropython-lib](https://github.com/pfalcon/micropython-lib).

I support only the official build of MicroPython. The library code guaranteed
to work with this build is in [micropython-lib](https://github.com/micropython/micropython-lib).
Most of the resources in here should work with Paul's forks (most work with
CPython).

Most documentation and code in this repository assumes the current official
version of `uasyncio`. This is V2.0 from
[micropython-lib](https://github.com/micropython/micropython-lib).
If release build of MicroPython V1.10 or later is used, V2.0 is incorporated
and no installation is required. Some examples illustrate the features of the
`fast_io` fork and therefore require this version.

See [tutorial](./TUTORIAL.md#installing-uasyncio-on-bare-metal) for
installation instructions where a realease build is not used.

# 3. uasyncio development state

These notes are intended for users familiar with `asyncio` under CPython.

The MicroPython language is based on CPython 3.4. The `uasyncio` library
supports a subset of the CPython 3.4 `asyncio` library with some V3.5
extensions. In addition there are non-standard extensions to optimise services
such as millisecond level timing and task cancellation. Its design focus is on
high performance and scheduling is performed without RAM allocation.

The `uasyncio` library supports the following Python 3.5 features:

 * `async def` and `await` syntax.
 * Awaitable classes (using `__iter__` rather than `__await__`).
 * Asynchronous context managers.
 * Asynchronous iterators.
 * Event loop methods `call_soon` and `call_later`.
 * `sleep(seconds)`.

It supports millisecond level timing with the following:

 * Event loop method `call_later_ms`
 * uasyncio `sleep_ms(time)`

`uasyncio` V2 supports coroutine timeouts and cancellation.

 * `wait_for(coro, t_secs)` runs `coro` with a timeout.
 * `cancel(coro)` tags `coro` for cancellation when it is next scheduled.

Classes `Task` and `Future` are not supported.

## 3.1 Asynchronous I/O

Asynchronous I/O (`StreamReader` and `StreamWriter` classes) support devices
with streaming drivers, such as UARTs and sockets. It is now possible to write
streaming device drivers in Python.

## 3.2 Time values

For timing asyncio uses floating point values of seconds. The `uasyncio.sleep`
method accepts floats (including sub-second values) or integers. Note that in
MicroPython the use of floats implies RAM allocation which incurs a performance
penalty. The design of `uasyncio` enables allocation-free scheduling. In
applications where performance is an issue, integers should be used and the
millisecond level functions (with integer arguments) employed where necessary.

The `loop.time` method returns an integer number of milliseconds whereas
CPython returns a floating point number of seconds. `call_at` follows the
same convention.

# 4. The "fast_io" version.

Official `uasyncio` suffers from high levels of latency when scheduling I/O in
typical applications. It also has an issue which can cause bidirectional
devices such as UART's to block. The `fast_io` version fixes the bug. It also
provides a facility for reducing I/O latency which can substantially improve
the performance of stream I/O drivers. It provides other features aimed at
providing greater control over scheduling behaviour.

To take advantage of the reduced latency device drivers should be written to
employ stream I/O. To operate at low latency they are simply run under the
`fast_io` version. The [tutorial](./TUTORIAL.md#64-writing-streaming-device-drivers)
has details of how to write streaming drivers.

The current `fast_io` version 0.24 fixes an issue with task cancellation and
timeouts. In `uasyncio` version 2.0, where a coroutine is waiting on a
`sleep()` or on I/O, a timeout or cancellation is deferred until the coroutine
is next scheduled. This introduces uncertainty into when the coroutine is
stopped. This issue is also addressed in Paul Sokolovsky's fork.

## 4.1 A Pyboard-only low power module

This is documented [here](./lowpower/README.md). In essence a Python file is
placed on the device which configures the `fast_io` version of `uasyncio` to
reduce power consumption at times when it is not busy. This provides a means of
using `uasyncio` in battery powered projects.

# 5. The asyn.py library

This library ([docs](./PRIMITIVES.md)) provides 'micro' implementations of the
`asyncio` synchronisation primitives.
[CPython docs](https://docs.python.org/3/library/asyncio-sync.html)

It also supports a `Barrier` class to facilitate coroutine synchronisation.

Coroutine cancellation is performed in an efficient manner in `uasyncio`. The
`asyn` library uses this, further enabling the cancelling coro to pause until
cancellation is complete. It also provides a means of checking the 'running'
status of individual coroutines.

A lightweight implementation of `asyncio.gather` is provided.
