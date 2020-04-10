# 1, Guide to uasyncio V3

The new release of `uasyncio` is pre-installed in current daily firmware 
builds. This complete rewrite of `uasyncio` supports CPython 3.8 syntax. A
design aim is that it should be be a compatible subset of `asyncio`.

These notes and the tutorial should be read in conjunction with
[the official docs](http://docs.micropython.org/en/latest/library/uasyncio.html)

There is a new tutorial for V3.

#### [V3 Tutorial](./TUTORIAL.md)

# 2. Overview

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

It includes the followiing CPython compatible synchronisation primitives:
 * `Event`.
 * `Lock`.
 * `gather`.

This repo includes code for the CPython primitives which are not yet officially
supported.

The `Future` class is not supported, nor are the `event_loop` methods
`call_soon`, `call_later`, `call_at`.

# 3. Porting applications from V2

Many applications using the coding style advocated in the V2 tutorial will work
unchanged. However there are changes, firstly to `uasyncio` syntax and secondly
related to modules in this repository.

## 3.1 Syntax changes

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
[in the tutorial](./TUTORIAL.md#412-portable-code).

## 3.2 Modules from this repository

Modules `asyn.py` and `aswitch.py` are deprecated for V3 applications. See
[the tutorial](./TUTORIAL.md) for V3 replacements.

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

I am hoping that the above will be replaced by more efficient official built-in
versions. To date those listed as "already incorporated" have been and should
be used.

### 3.2.2 Synchronisation primitives (old asyn.py)

Applications using `asyn.py` should no longer import that module. Equivalent
functionality may now be found in the `primitives` directory: this is
implemented as a Python package enabling RAM savings.

These features in `asyn.py` were workrounds for bugs in V2 and should not be
used with V3:
 * The cancellation decorators and classes (cancellation works as per CPython).
 * The nonstandard support for `gather` (now properly supported).

The `Event` class in `asyn.py` is now replaced by `Message` - this is discussed
in [the tutorial](./TUTORIAL.md).

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
