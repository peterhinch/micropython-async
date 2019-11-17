# 1. Asynchronous programming in MicroPython

CPython supports asynchronous programming via the `asyncio` library.
MicroPython provides `uasyncio` which is a subset of this, optimised for small
code size and high performance on bare metal targets. This repository provides
documentation, tutorial material and code to aid in its effective use. It also
contains an optional `fast_io` variant of `uasyncio`.

Damien has completely rewritten `uasyncio`. Its release is likely to be
imminent, see
[PR5332](https://github.com/micropython/micropython/pull/5332) and [section 3.1](./README.md#31-the-new_version).

## The fast_io variant

This comprises two parts.  
 1. The [fast_io](./FASTPOLL.md) version of `uasyncio` is a "drop in"
 replacement for the official version providing bug fixes, additional
 functionality and, in certain respects, higher performance.
 2. An optional extension module enabling the [fast_io](./FASTPOLL.md) version
 to run with very low power draw. This is Pyboard-only including Pyboard D.

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

Paul Sokolovsky (`uasyncio` author) has released versions of `uasyncio` which
supercede the official version. His latest version is that on PyPi and requires
his [Pycopy](https://github.com/pfalcon/micropython) fork of MicroPython
firmware. His `uasyncio` code may also be found in
[his fork of micropython-lib](https://github.com/pfalcon/micropython-lib).

I support only the official build of MicroPython. The library code guaranteed
to work with this build is in [micropython-lib](https://github.com/micropython/micropython-lib).
Most of the resources in here should work with Paul's forks (most work with
CPython).

Most documentation and code in this repository assumes the current official
version of `uasyncio`. This is V2.0 from
[micropython-lib](https://github.com/micropython/micropython-lib).
It is recommended to use MicroPython firmware V1.11 or later. On many platforms
`uasyncio` is incorporated and no installation is required.

Some examples illustrate features of the `fast_io` fork and therefore require
this version.

See [tutorial](./TUTORIAL.md#installing-uasyncio-on-bare-metal) for
installation instructions where `uasyncio` is not pre-installed.

# 3. uasyncio development state

## 3.1 The new version

This complete rewrite of `uasyncio` supports CPython 3.8 syntax. A design aim
is that it should be be a compatible subset of `asyncio`. Many applications
using the coding style advocated in the tutorial will work unchanged. The
following features will involve minor changes to application code:

 * Task cancellation: `cancel` is now a method of a `Task` instance.
 * Event loop methods: `call_at`, `call_later`, `call_later_ms`  and
 `call_soon` are no longer supported. In CPython docs these are
 [lightly deprecated](https://docs.python.org/3/library/asyncio-eventloop.html#preface)
 in application code; there are simple workrounds.
 * `yield` in coroutines should be replaced by `await asyncio.sleep_ms(0)`:
 this is in accord with CPython where `yield` will produce a syntax error.
 * Awaitable classes: currently under discussion. The `__iter__` method works
 but `yield` should be replaced by `await asyncio.sleep_ms(0)`. As yet I have
 found no way to write an awaitable class compatible with the new `uasyncio`
 and which does not throw syntax errors under CPython 3.8/`asyncio`.

### 3.1.1 Implications for this repository

It is planned to retain V2 under a different name. The new version fixes bugs
which have been outstanding for a long time. In my view V2 is best viewed as
deprecated. I will retain V2-specific code and docs in a separate directory,
with the rest of this repo being adapted for the new version.

#### 3.1.1.1 Tutorial

This requires only minor changes.

#### 3.1.1.2 Fast I/O

The `fast_io` fork is incompatible and will be relegated to the V2 directory.

The new version's design greatly simplifies the implementation of fast I/O:
I therefore hope the new `uasyncio` will include it. The other principal aims
were to provide workrounds for bugs now fixed. If `uasyncio` includes fast I/O
there is no reason to fork the new version; other `fast_io` features will be
lost unless Damien sees fit to implement them. The low priority task option is
little used and arguably is ill-conceived: I will not be advocating for its
inclusion.

#### 3.1.1.3 Synchronisation Primitives

The CPython `asyncio` library supports these synchronisation primitives:
 * `Lock` - already incorporated in new `uasyncio`.
 * `Event` - already incorporated.
 * `gather` - already incorporated.
 * `Semaphore` and `BoundedSemaphore`. My classes work under new version.
 * `Condition`. Works under new version.
 * `Queue`. This was implemented by Paul Sokolvsky in `uasyncio.queues`.
 
Incorporating these will produce more efficient implementations; my solutions
were designed to work with stock `uasyncio` V2.

The `Event` class in `asyn.py` provides a nonstandard option to supply a data
value to the `.set` method and to retrieve this with `.value`. It is also an
awaitable class. I will support these by subclassing the native `Event`.

The following work under new and old versions:
 * `Barrier` (now adapted).
 * `Delay_ms` (this and the following in aswitch.py)
 * `Switch`
 * `Pushbutton`

The following were workrounds for bugs and omissions in V2 which are now fixed.
They will be removed.  
 * The cancellation decorators and classes (cancellation works as per CPython).
 * The nonstandard support for `gather` (now properly supported).

## 3.2 The current version V2.0

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

## 3.2.1 Asynchronous I/O

Asynchronous I/O (`StreamReader` and `StreamWriter` classes) support devices
with streaming drivers, such as UARTs and sockets. It is now possible to write
streaming device drivers in Python.

## 3.2.2 Time values

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
