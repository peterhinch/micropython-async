# 1. Guide to uasyncio V3

This release of `uasyncio` is pre-installed on all platforms except severely
constrained ones such as the 1MB ESP8266. This rewrite of `uasyncio` supports
CPython 3.8 syntax. A design aim is that it should be be a compatible subset of
`asyncio`. The current version is 3.0.0.

These notes and the tutorial should be read in conjunction with
[the official docs](http://docs.micropython.org/en/latest/library/uasyncio.html)

## 1.1 Resources for V3

This repo contains the following:

### [V3 Tutorial](./docs/TUTORIAL.md)

Intended for users with all levels of experience with asynchronous programming.

### Test/demo scripts  

Documented in the tutorial.

### Synchronisation primitives  

Documented in the tutorial. Comprises:
 * CPython primitives not yet officially supported.
 * Two additional primitives `Barrier` and `Message`.
 * Classes for interfacing switches and pushbuttons.
 * A software retriggerable monostable timer class, similar to a watchdog.

### A scheduler

This [lightweight scheduler](./docs/SCHEDULE.md) enables tasks to be scheduled
at future times. These can be assigned in a flexible way: a task might run at
4.10am on Monday and Friday if there's no "r" in the month.

### Asynchronous device drivers  

These device drivers are intended as examples of asynchronous code which are
useful in their own right:

 * [GPS driver](./docs/GPS.md) Includes various GPS utilities.
 * [HTU21D](./docs/HTU21D.md) Temperature and humidity sensor.
 * [I2C](./docs/I2C.md) Use Pyboard I2C slave mode to implement a UART-like
 asynchronous stream interface. Uses: communication with ESP8266, or (with
 coding) interface a Pyboard to I2C masters.
 * [NEC IR](./docs/NEC_IR.md) A receiver for signals from IR remote controls
 using the popular NEC protocol.
 * [HD44780](./docs/hd44780.md) Driver for common character based LCD displays
 based on the Hitachi HD44780 controller.

### Event-based programming

[A guide](./docs/EVENTS.md) to a writing applications and device drivers which
largely does away with callbacks.

### A monitor

This [monitor](https://github.com/peterhinch/micropython-monitor) enables a
running `uasyncio` application to be monitored using a Pi Pico, ideally with a
scope or logic analyser. If designing hardware it is suggested to provide
access to a UART tx pin, or alternatively to three GPIO pins, to enable this to
be used if required.

![Image](https://github.com/peterhinch/micropython-monitor/raw/master/images/monitor.jpg)

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
