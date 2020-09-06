# 1. uasyncio V2

This repo also contains an optional `fast_io` variant of `uasyncio` V2. This
variant offers high I/O performance and also includes workrounds for many of
the bugs in V2. (Bugs properly fixed in V3.)

## Reasons for running V2

In general I recommend V3, especially for new projects. It is better in every
respect bar one: the `fast_io` variant of V2 currently offers superior I/O
performance, relative both to V2 and V3.

The main reason for running official V2 is that many existing libraries have
not yet been ported to V3. Some will run without change, but those using more
advanced features of `uasyncio` may not.

## 1.1 Resources

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
 
## 1.2 The fast_io variant

This comprises two parts.  
 1. The [fast_io](./FASTPOLL.md) version of `uasyncio` is a "drop in"
 replacement for the official version 2 providing bug fixes, additional
 functionality and, in certain respects, higher performance.
 2. An optional extension module enabling the [fast_io](./FASTPOLL.md) version
 to run with very low power draw. This is Pyboard-only including Pyboard D.

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
stopped.

## 1.2.1 A Pyboard-only low power module

This is documented [here](./lowpower/README.md). In essence a Python file is
placed on the device which configures the `fast_io` version of `uasyncio` to
reduce power consumption at times when it is not busy. This provides a means of
using `uasyncio` in battery powered projects. This is decidedly experimental:
hopefully `uasyncio` V3 will introduce power saving in a less hacky manner.

## 1.3 Under the hood

[Under the hood](./UNDER_THE_HOOD.md) A guide to help understand the V2
`uasyncio` code. For scheduler geeks and those wishing to modify `uasyncio`.

## 1.4 Synchronisation Primitives

All solutions listed below work with stock `uasyncio` V2 or `fast_io`.

The CPython `asyncio` library supports these synchronisation primitives:
 * `Lock`
 * `Event`
 * `gather`
 * `Semaphore` and `BoundedSemaphore`.
 * `Condition`.
 * `Queue`. This was implemented by Paul Sokolvsky in `uasyncio.queues`.

See [CPython docs](https://docs.python.org/3/library/asyncio-sync.html).

The file `asyn.py` contains implementations of these, also
 * `Barrier` An additional synchronisation primitive.
 * Cancellation decorators and classes: these are workrounds for the bug where
 in V2 cancellation does not occur promptly.
 * Support for `gather`.

The `Event` class in `asyn.py` provides a nonstandard option to supply a data
value to the `.set` method and to retrieve this with `.value`. It is also an
awaitable class.

#### These are documented [here](./PRIMITIVES.md)

## 1.5 Switches, Pushbuttons and Timeouts

The file `aswitch.py` provides support for:
 * `Delay_ms` A software retriggerable monostable or watchdog.
 * `Switch` Debounced switch and pushbutton classes with callbacks.
 * `Pushbutton`

#### It is documented [here](./DRIVERS.md)

# 2. Version 2.0 usage notes

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

## 2.1 Asynchronous I/O

Asynchronous I/O (`StreamReader` and `StreamWriter` classes) support devices
with streaming drivers, such as UARTs and sockets. It is now possible to write
streaming device drivers in Python.

## 2.2 Time values

For timing asyncio uses floating point values of seconds. The `uasyncio.sleep`
method accepts floats (including sub-second values) or integers. Note that in
MicroPython the use of floats implies RAM allocation which incurs a performance
penalty. The design of `uasyncio` enables allocation-free scheduling. In
applications where performance is an issue, integers should be used and the
millisecond level functions (with integer arguments) employed where necessary.

The `loop.time` method returns an integer number of milliseconds whereas
CPython returns a floating point number of seconds. `call_at` follows the
same convention.
