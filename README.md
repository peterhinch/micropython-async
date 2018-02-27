# 1. The MicroPython uasyncio library

This GitHub repository consists of the following parts:
 * [A tutorial](./TUTORIAL.md) An introductory tutorial on asynchronous
 programming and the use of the uasyncio library is offered. This is a work in
 progress, not least because uasyncio is not yet complete.
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
 * [A modified uasyncio](./FASTPOLL.md) This incorporates a simple priority
 mechanism. With suitable application design this improves the rate at which
 devices can be polled and improves the accuracy of time delays. Also provides
 for low priority tasks which are only scheduled when normal tasks are paused.
 NOTE: this requires uasyncio V2.0.
 * [Communication between devices](./syncom_as/README.md) Enables MicroPython
 boards to communicate without using a UART. Primarily intended to enable a
 a Pyboard-like device to achieve bidirectional communication with an ESP8266.

# 2. Version and installation of uasyncio

The documentation and code in this repository are based on `uasyncio` version
2.0, which is the version on PyPi. This requires firmware dated 22nd Feb 2018
or later.

Version 2.0 brings only one API change over V1.7.1, namely the arguments to
`get_event_loop()`. Unless using the priority version all test programs and
code samples use default args so will work under either version. The priority
version requires the later version and firmware.

[Paul Sokolovsky's library](https://github.com/pfalcon/micropython-lib) has the
latest `uasyncio` code. At the time of writing (Feb 27th 2018) the version in
[micropython-lib](https://github.com/micropython/micropython-lib) is 1.7.1.

See [tutorial](./TUTORIAL.md#installing-uasyncio-on-bare-metal) for
installation instructions.

# 3. uasyncio development state

These notes are intended for users familiar with `asyncio` under CPython.

The MicroPython language is based on CPython 3.4. The `uasyncio` library
supports a subset of the CPython 3.4 `asyncio` library with some V3.5
extensions. In addition there are nonstandard extensions to optimise services
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

As of `uasyncio.core` V1.7.1 (7th Jan 2018) it supports coroutine timeouts and
cancellation.

 * `wait_for(coro, t_secs)` runs `coro` with a timeout.
 * `cancel(coro)` tags `coro` for cancellation when it is next scheduled.

Classes `Task` and `Future` are not supported.

## 3.1 Asynchronous I/O

Asynchronous I/O works with devices whose drivers support streaming, such as
UARTs.

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

# 4. The asyn.py library

This library ([docs](./PRIMITIVES.md)) provides 'micro' implementations of the
`asyncio` synchronisation primitives.
[CPython docs](https://docs.python.org/3/library/asyncio-sync.html)

It also supports a `Barrier` class to facilitate coroutine synchronisation.

Coroutine cancellation is performed in an efficient manner in `uasyncio`. The
`asyn` library uses this, further enabling the cancelling coro to pause until
cancellation is complete. It also provides a means of checking the 'running'
status of individual coroutines.

A lightweight implementation of `asyncio.gather` is provided.
