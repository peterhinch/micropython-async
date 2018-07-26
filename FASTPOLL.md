# fast_io: A modified version of uasyncio

MicroPython firmware now enables device drivers for stream devices to be
written in Python, via `uio.IOBase`. This mechanism can be applied to any
situation where a piece of hardware or an asynchronously set flag needs to be
polled. Such polling is efficient because it is handled in C using
`select.poll`, and because the coroutine accessing the device is descheduled
until polling succeeds.

Unfortunately current `uasyncio` polls I/O with a relatively high degree of
latency. It also has a bug whereby bidirectional devices such as UARTS could
fail to handle concurrent input and output.

This version has the following changes:
 * I/O can optionally be handled at a higher priority than other coroutines
 [PR287](https://github.com/micropython/micropython-lib/pull/287).
 * The bug with read/write device drivers is fixed (forthcoming PR).
 * An assertion failure is produced if `create_task` or `run_until_complete`
 is called with a generator function [PR292](https://github.com/micropython/micropython-lib/pull/292).

A key advantage of this version is that priority device drivers are written
entirely by using the officially-supported technique for writing stream I/O
drivers. If official `uasyncio` acquires a means of prioritising I/O by other
means than by these proposals, application code changes are likely to be
minimal. Using the priority mechanism in this version requires a change to just
one line of code compared to an application running under the official version.

The high priority mechanism formerly provided in `asyncio_priority.py` is
replaced with a faster and more efficient way of handling asynchronous events
with minimum latency. Consequently `asyncio_priority.py` is obsolete and should
be deleted from your system. The facility for low priority coros is currently
unavailable but will be reinstated.

This modified version also provides for ultra low power consumption using a
module documented [here](./lowpower/README.md).

###### [Main README](./README.md)

# Contents

 1. [Installation](./FASTPOLL.md#1-installation)  
  1.1 [Benchmarks](./FASTPOLL.md#11-benchmarks) Benchmark and demo programs.  
 2. [Rationale](./FASTPOLL.md#2-rationale)  
  2.1 [Latency](./FASTPOLL.md#21-latency)  
  2.2 [Timing accuracy](./FASTPOLL.md#22-timing-accuracy)  
  2.3 [Polling in uasyncio](./FASTPOLL.md#23-polling-in-usayncio)  
 3. [The modified version](./FASTPOLL.md#3-the-modified-version)  
 4. [ESP Platforms](./FASTPOLL.md#4-esp-platforms)  
 5. [Background](./FASTPOLL.md#4-background)  

# 1. Installation

Install and test uasyncio on the target hardware. Replace `core.py` and
`__init__.py` with the files in the `fast_io` directory.

In MicroPython 1.9 `uasyncio` was implemented as a frozen module on the
ESP8266. To install this version it is necessary to build the firmware with the
above two files implemented as frozen bytecode. See
[ESP Platforms](./FASTPOLL.md#6-esp-platforms) for general comments on the
suitability of ESP platforms for systems requiring fast response.

## 1.1 Benchmarks

The benchmarks directory contains files demonstrating the performance gains
offered by prioritisation. They also offer illustrations of the use of these
features. Documentation is in the code.

 * `benchmarks/rate.py` Shows the frequency with which uasyncio schedules
 minimal coroutines (coros).
 * `benchmarks/rate_esp.py` As above for ESP32 and ESP8266.
 * `benchmarks/rate_fastio.py` Measures the rate at which coros can be scheduled
 if the fast I/O mechanism is used but no I/O is pending.
 * `fast_io/ms_timer.py` Provides higher precision timing than `wait_ms()`.
 * `fast_io/ms_timer.py` Test/demo program for above.
 * `fast_io/pin_cb.py` Demo of an I/O device driver which causes a pin state
 change to trigger a callback.
 * `fast_io/pin_cb_test.py` Demo of above.

With the exception of `rate_fastio`, benchmarks can be run against the official
and priority versions of usayncio.

# 2. Rationale

Applications may need to poll a hardware device or a flag set by an interrupt
service routine (ISR). An overrun may occur if the scheduling of the polling
coroutine (coro) is subject to excessive latency. Fast devices with interrupt
driven drivers (such as the UART) need to buffer incoming data during any
latency period. Lower latency reduces the buffer size requirement.

Further, a coro issuing `await asyncio.sleep_ms(t)` may block for much longer
than `t` depending on the number and design of other coros which are pending
execution. Delays can easily exceed the nominal value by an order of magnitude.

This variant mitigates this by providing a means of scheduling I/O at a higher
priority than other coros: if an I/O queue is specified, I/O devices are polled
on every iteration of the scheduler. This enables faster response to real time
events and also enables higher precision millisecond-level delays to be
realised.

## 2.1 Latency

Coroutines in uasyncio which are pending execution are scheduled in a "fair"
round-robin fashion. Consider these functions:

```python
async def foo():
    while True:
        yield
        # code which takes 4ms to complete

async def handle_isr():
    global isr_has_run
    while True:
        if isr_has_run:
            # read and process data
            isr_has_run = False
        yield
```

Assume a hardware interrupt handler sets the `isr_has_run` flag, and that we
have ten instances of `foo()` and one instance of `handle_isr()`. When
`handle_isr()` issues `yield`, its execution will pause for 40ms while each
instance of `foo()` is scheduled and performs one iteration. This may be
unacceptable: it may be necessary to poll and respond to the flag at a rate
sufficient to avoid overruns.

In this version `handle_isr()` would be rewritten as a stream device driver
which could be expected to run with latency of just over 4ms.

### 2.1.1 I/O latency

The current version of `uasyncio` has even higher levels of latency for I/O
scheduling. In the above case of ten coros using 4ms of CPU time between zero
delay yields, the latency of an I/O driver would be 80ms.

###### [Contents](./FASTPOLL.md#contents)

## 2.2 Timing accuracy

Consider these functions:

```python
async def foo():
    while True:
        await asyncio.sleep(0)
        # code which takes 4ms to complete

async def fast():
    while True:
        # Code omitted
        await asyncio.sleep_ms(15)
        # Code omitted
```

Again assume ten instances of `foo()` and one of `fast()`. When `fast()`
issues `await asyncio.sleep_ms(15)` it will not see a 15ms delay. During the
15ms period `foo()` instances will be scheduled. When the delay elapses,
`fast()` will compete with pending `foo()` instances.

This results in variable delays up to 55ms (10 tasks * 4ms + 15ms). A
`MillisecTimer` class is provided which uses stream I/O to achieve a relatively
high precision delay:

```python
async def timer_test(n):
    timer = ms_timer.MillisecTimer()
    while True:
        await timer(30)  # More precise timing
        # Code
```

The test program `fast_io/ms_timer_test.py` illustrates three instances of a
coro with a 30ms nominal timer delay, competing with ten coros which yield with
a zero delay between hogging the CPU for 10ms. Using normal scheduling the 30ms
delay is actually 300ms. With fast I/O it is 30-34ms.

###### [Contents](./FASTPOLL.md#contents)

## 2.3 Polling in uasyncio

The asyncio library provides various mechanisms for polling a device or flag.
Aside from a polling loop these include awaitable classes and asynchronous
iterators. If an awaitable class's `__iter__()` method simply returns the state
of a piece of hardware, there is no performance gain over a simple polling
loop.

This is because uasyncio schedules tasks which yield with a zero delay,
together with tasks which have become ready to run, in a "fair" round-robin
fashion. This means that a task waiting on a zero delay will be rescheduled
only after the scheduling of all other such tasks (including timed waits whose
time has elapsed).

The `fast_io` version enables awaitable classes and asynchronous iterators to
run with lower latency by designing them to use the stream I/O mechanism. The
program `fast_io/ms_timer.py` provides an example.

###### [Contents](./FASTPOLL.md#contents)

# 3. The modified version

The `fast_io` version adds an `ioq_len=0` argument to `get_event_loop`. The
zero default causes the scheduler to operate as per the official version. If an
I/O queue length > 0 is provided, I/O performed by `StreamReader` and
`StreamWriter` objects will be prioritised over other coros.

Arguments to `get_event_loop()`:  
 1. `runq_len` Length of normal queue. Default 16 tasks.
 2. `waitq_len` Length of wait queue. Default 16.
 3. `ioq_len` Length of I/O queue. Default 0.

Device drivers which are to be capable of running at high priority should be
written to use stream I/O: see
[Writing IORead device drivers](./TUTORIAL.md#54-writing-ioread-device-drivers).

The `fast_io` version will schedule I/O whenever the `ioctl` reports a ready
status. This implies that devices which become ready very soon after being
serviced can hog execution. This is analogous to the case where an interrupt
service routine is called at an excessive frequency.

This behaviour may be desired where short bursts of fast data are handled.
Otherwise drivers of such hardware should be designed to avoid hogging, using
techniques like buffering or timing.

The version also supports a `version` variable containing 'fast_io'. This
enables the presence of this version to be determined at runtime.

It also supports a `got_event_loop()` function returning a `bool`: `True` if
the event loop has been instantiated. The purpose is to enable code which uses
the event loop to raise an exception if the event loop was not instantiated.

```python
class Foo():
    def __init__(self):
        if asyncio.got_event_loop():
            loop = asyncio.get_event_loop()
            loop.create_task(self._run())
        else:
            raise OSError('Foo class requires an event loop instance')
```
This avoids subtle errors:
```python
import uasyncio as asyncio
bar = Bar()  # Constructor calls get_event_loop()
# and renders these args inoperative
loop = asyncio.get_event_loop(runq_len=40, waitq_len=40)
```

###### [Contents](./FASTPOLL.md#contents)

# 4. ESP Platforms

It should be noted that the response of the ESP8266 to hardware interrupts is
remarkably slow. This also appears to apply to ESP32 platforms. Consider
whether a response in the high hundreds of μs meets project requirements; also
whether a priority mechanism is needed on hardware with such poor realtime
performance.

# 5. Background

This has been discussed in detail
[in issue 2989](https://github.com/micropython/micropython/issues/2989).

A further discussion on the subject of using the ioread mechanism to achieve
fast scheduling took place
[in issue 2664](https://github.com/micropython/micropython/issues/2664).

Support was finally [added here](https://github.com/micropython/micropython/pull/3836).
