# 1. Guide to uasyncio V3

The new release of `uasyncio` is pre-installed in current daily firmware 
builds and will be found in release builds starting with V1.13. This complete
rewrite of `uasyncio` supports CPython 3.8 syntax. A design aim is that it
should be be a compatible subset of `asyncio`.

These notes and the tutorial should be read in conjunction with
[the official docs](http://docs.micropython.org/en/latest/library/uasyncio.html)

## 1.1 Resources for V3

This repo contains the following:

### [V3 Tutorial](./docs/TUTORIAL.md)  
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

# 3. Porting applications from V2

Many applications using the coding style advocated in the V2 tutorial will work
unchanged. However there are changes, firstly to `uasyncio` itself and secondly
to modules in this repository.

## 3.1 Changes to uasyncio

### 3.1.1 Syntax changes

 * Task cancellation: `cancel` is now a method of a `Task` instance.
 * Event loop methods: `call_at`, `call_later`, `call_later_ms`  and
 `call_soon` are no longer supported. In CPython docs these are
 [lightly deprecated](https://docs.python.org/3/library/asyncio-eventloop.html#preface)
 in application code; there are simple workrounds.
 * `yield` in coroutines must be replaced by `await asyncio.sleep_ms(0)`:
 this is in accord with CPython where `yield` will produce a syntax error.
 * Awaitable classes. The `__iter__` method works but `yield` must be replaced
 by `await asyncio.sleep_ms(0)`.

It is possible to write an awaitable class with code portable between
MicroPython and CPython 3.8. This is discussed
[in the tutorial](./docs/TUTORIAL.md#412-portable-code).

### 3.1.2 Change to stream I/O

Classes based on `uio.IOBase` will need changes to the `write` method. See
[tutorial](./docs/TUTORIAL.md#64-writing-streaming-device-drivers).

### 3.1.3 Early task creation

It is [bad practice](https://github.com/micropython/micropython/issues/6174)
to create tasks before issuing `asyncio.run()`. CPython 3.8 throws if you do.
Such code can be ported by wrapping functions that create tasks in a
coroutine as below.

There is a subtlety affecting code that creates tasks early:
`loop.run_forever()` did just that, never returning and scheduling all created
tasks. By contrast `asyncio.run(coro())` terminates when the coro does. Typical
firmware applications run forever so the coroutine started by `.run()` must
`await` a continuously running task. This may imply exposing an asynchronous
method which runs forever:

```python
async def main():
   obj = MyObject()  # Constructor creates tasks
   await obj.run_forever()  # Never terminates

def run():  # Entry point
    try:
        asyncio.run(main())
    finally:
        asyncio.new_event_loop()
```

## 3.2 Modules from this repository

Modules `asyn.py` and `aswitch.py` are deprecated for V3 applications. See
[the tutorial](./docs/TUTORIAL.md#3-synchronisation) for V3 replacements which
are more RAM-efficient.

### 3.2.1 Synchronisation primitives

These were formerly provided in `asyn.py` and may now be found in the
`primitives` directory, along with additional unofficial primitives.

The CPython `asyncio` library supports these synchronisation primitives:
 * `Lock` - already incorporated in new `uasyncio`.
 * `Event` - already incorporated.
 * `gather` - already incorporated.
 * `Semaphore` and `BoundedSemaphore`. In this repository.
 * `Condition`. In this repository.
 * `Queue`. In this repository.

The above unofficial primitives are CPython compatible. Using future official
versions will require a change to the import statement only.

### 3.2.2 Synchronisation primitives (old asyn.py)

Applications using `asyn.py` should no longer import that module. Equivalent
functionality may now be found in the `primitives` directory: this is
implemented as a Python package enabling RAM savings. The new versions are also
more efficient, replacing polling with the new `Event` class.

These features in `asyn.py` were workrounds for bugs in V2 and should not be
used with V3:
 * The cancellation decorators and classes (cancellation works as per CPython).
 * The nonstandard support for `gather` (now properly supported).

The `Event` class in `asyn.py` is now replaced by `Message` - this is discussed
in [the tutorial](./docs/TUTORIAL.md#36-message).

### 3.2.3 Switches, Pushbuttons and delays (old aswitch.py)

Applications using `aswitch.py` should no longer import that module. Equivalent
functionality may now be found in the `primitives` directory: this is
implemented as a Python package enabling RAM savings.

New versions are provided in this repository. Classes:
 * `Delay_ms` Software retriggerable monostable (watchdog-like object).
 * `Switch` Debounced switch with close and open callbacks.
 * `Pushbutton` Pushbutton with double-click and long press callbacks.

# 4. Outstanding issues with V3

V3 is still a work in progress. The following is a list of issues which I hope
will be addressed in due course.

## 4.1 Fast I/O scheduling

There is currently no support for this: I/O is scheduled in round robin fashion
with other tasks. There are situations where this is too slow, for example in
I2S applications and ones involving multiple fast I/O streams, e.g. from UARTs.
In these applications there is still a use case for the `fast_io` V2 variant.

## 4.2 Synchronisation primitives

These CPython primitives are outstanding:
 * `Semaphore`.
 * `BoundedSemaphore`.
 * `Condition`.
 * `Queue`.
