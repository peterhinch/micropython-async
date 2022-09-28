# 1. Guide to uasyncio

MicroPython's `uasyncio` is pre-installed on all platforms except severely
constrained ones such as the 1MB ESP8266. It supports CPython 3.8 syntax and
aims to be a compatible subset of `asyncio`. The current version is 3.0.0.

## 1.1 Documents

[uasyncio official docs](http://docs.micropython.org/en/latest/library/uasyncio.html)

[Tutorial](./docs/TUTORIAL.md) Intended for users with all levels of experience
of asynchronous programming, including beginners.

[Drivers](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/DRIVERS.md)
describes device drivers for switches, pushbuttons, ESP32 touch buttons, ADC's
and incremental encoders.

[Interrupts](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/INTERRUPTS.md)
is a guide to interfacing interrupts to `uasyncio`.

[Event-based programming](./docs/EVENTS.md) is a guide to a way of writing
applications and device drivers which largely does away with callbacks. Assumes
some knowledge of `uasyncio`.

## 1.2 Debugging tools

[aiorepl](https://github.com/micropython/micropython-lib/tree/master/micropython/aiorepl)
This official tool enables an application to launch a REPL which is active
while the application is running. From this you can modify and query the
application and run `uasyncio` scripts concurrently with the running
application.

[monitor](https://github.com/peterhinch/micropython-monitor) enables a running
`uasyncio` application to be monitored using a Pi Pico, ideally with a scope or
logic analyser. Normally requires only one GPIO pin on the target.

![Image](https://github.com/peterhinch/micropython-monitor/raw/master/images/monitor.jpg)

## 1.3 Resources in this repo

### 1.3.1 Test/demo scripts  

Documented in the [tutorial](./docs/TUTORIAL.md).

### 1.3.2 Synchronisation primitives  

Documented in the [tutorial](./docs/TUTORIAL.md). Comprises:
 * Implementations of unsupported CPython primitives including `barrier`,
 `queue` and others.
 * An additional primitive `Message`.
 * A software retriggerable monostable timer class `Delay_ms`, similar to a
 watchdog.
 * Two primitives enabling waiting on groups of `Event` instances.

### 1.3.3 Asynchronous device drivers

These are documented
[here](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/DRIVERS.md):
 * Classes for interfacing switches, pushbuttons and ESP32 touch buttons.
 * Drivers for ADC's
 * Drivers for incremental encoders.

### 1.3.4 A scheduler

This [lightweight scheduler](./docs/SCHEDULE.md) enables tasks to be scheduled
at future times. These can be assigned in a flexible way: a task might run at
4.10am on Monday and Friday if there's no "r" in the month.

### 1.3.5 Asynchronous interfaces  

These device drivers are intended as examples of asynchronous code which are
useful in their own right:

 * [GPS driver](./docs/GPS.md) Includes various GPS utilities.
 * [HTU21D](./docs/HTU21D.md) Temperature and humidity sensor.
 * [I2C](./docs/I2C.md) Use Pyboard I2C slave mode to implement a UART-like
 asynchronous stream interface. Uses: communication with ESP8266, or (with
 coding) to interface a Pyboard to I2C masters.
 * [NEC IR](./docs/NEC_IR.md) A receiver for signals from IR remote controls
 using the popular NEC protocol.
 * [HD44780](./docs/hd44780.md) Driver for common character based LCD displays
 based on the Hitachi HD44780 controller.

# 2. V3 Overview

These notes are intended for users familiar with `asyncio` under CPython.

The MicroPython language is based on CPython 3.4. The `uasyncio` library now
supports a subset of the CPython 3.8 `asyncio` library. There are non-standard
extensions to optimise services such as millisecond level timing. Its design
focus is on high performance. Scheduling runs without RAM allocation.

The `uasyncio` library supports the following features:

 * `async def` and `await` syntax.
 * Awaitable classes (using `__iter__` rather than `__await__`).
 * Asynchronous context managers.
 * Asynchronous iterators.
 * `uasyncio.sleep(seconds)`.
 * Timeouts (`uasyncio.wait_for`).
 * Task cancellation (`Task.cancel`).
 * Gather.

It supports millisecond level timing with the following:
 * `uasyncio.sleep_ms(time)`

It includes the following CPython compatible synchronisation primitives:
 * `Event`.
 * `Lock`.
 * `gather`.

This repo includes code for the CPython primitives which are not yet officially
supported.

The `Future` class is not supported, nor are the `event_loop` methods
`call_soon`, `call_later`, `call_at`.

## 2.1 Outstanding issues with V3

V3 is still a work in progress. The following is a list of issues which I hope
will be addressed in due course.

### 2.1.1 Fast I/O scheduling

There is currently no support for this: I/O is scheduled in round robin fashion
with other tasks. There are situations where this is too slow and the scheduler
should be able to poll I/O whenever it gains control.

### 2.1.2 Synchronisation primitives

These CPython primitives are outstanding:
 * `Semaphore`.
 * `BoundedSemaphore`.
 * `Condition`.
 * `Queue`.
