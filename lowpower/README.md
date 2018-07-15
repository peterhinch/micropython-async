# An experimental low power usayncio adaptation

# 1. Introduction

This adaptation is specific to the Pyboard and compatible platforms, namely
those capable of running the `pyb` module. This module supports two low power
modes `standby` and `stop`
[see docs](http://docs.micropython.org/en/latest/pyboard/library/pyb.html).

Use of `standby` is simple in concept: the application runs and issues
`standby`. The board goes into a very low power mode until it is woken by one
of a limited set of external events, when it behaves similarly as after a hard
reset. In that respect a `uasyncio` application is no different from any other.
If the application can cope with the fact that execution state is lost during
the delay, it will correctly resume.

This adaptation modifies `uasyncio` such that it can enter `stop` mode for much
of the time, reducing power consumption. The two approaches can be combined,
with a device waking from `shutdown` to run a low power `uasyncio` application
before again entering `shutdown`.

The adaptation trades a reduction in scheduling performance for a substantial
reduction in power consumption.

Some general notes on low power Pyboard applications may be found
[here](https://github.com/peterhinch/micropython-micropower).

# 2. Installation

Ensure that the version of `uasyncio` in this repository is installed and
tested. Copy the file `rtc_time.py` to the device so that it is on `sys.path`.

The test program `lowpower.py` requires a link between pins X1 and X2 to enable
UART 4 to operate via a loopback.

# 3 Low power uasyncio operation

## 3.1 The official uasyncio package

The official `uasyncio` library is unsuited to low power operation for two
reasons. Firstly because of its method of I/O polling. In periods when no coro
is ready for execution, it determines the time when the most current coro will
be ready to run. It then calls `select.poll`'s `ipoll` method with a timeout
calculated on that basis. This consumes power.

The second issue is that it uses `utime`'s millisecond timing utilities for
timing. This ensures portability across MicroPython platforms. Unfortunately on
the Pyboard the clock responsible for `utime` stops for the duration of
`pyb.stop()`. This would cause all `uasyncio` timing to become highly
inaccurate.

## 3.2 The low power adaptation

If running on a Pyboard the version of `uasyncio` in this repo attempts to
import the file `rtc_time.py`. If this succeeds and there is no USB connection
to the board it derives its millisecond timing from the RTC; this continues to
run through `stop`.

To avoid the power drain caused by `select.poll` the user code must issue the
following:

```python
    loop = asyncio.get_event_loop()
    loop.create_task(rtc_time.lo_power(t))
```

This coro has a continuously running loop that executes `pyb.stop` before
yielding with a zero delay:

```python
    def lo_power(t_ms):
        rtc.wakeup(t_ms)
        while True:
            pyb.stop()
            yield
```

The design of the scheduler is such that, if at least one coro is pending with
a zero delay, polling will occur with a zero delay. This minimises power draw.
The significance of the `t` argument is detailed below.

### 3.2.1 Consequences of pyb.stop

#### 3.2.1.1 Timing Accuracy

A minor limitation is that the Pyboard RTC cannot resolve times of less than
4ms so there is a theoretical reduction in the accuracy of delays. In practice,
as explained in the [tutorial](../TUTORIAL.md), issuing

```python
    await asyncio.sleep_ms(t)
```

specifies a minimum delay: the maximum may be substantially higher depending on
the behaviour of other coroutines. The latency implicit in the `lo_power` coro
(see section 5.2) makes this issue largely academic.

#### 3.2.1.2 USB

Programs using `pyb.stop` disable the USB connection to the PC. This is
inconvenient for debugging so `rtc_time.py` detects an active USB connection
and disables power saving. This enables an application to be developed normally
via a USB connected PC. The board can then be disconnected from the PC and run
from a separate power source for power measurements.

Applications can detect which timebase is in use by issuing:

```python
import rtc_time
if rtc_time.use_utime:
    # Timebase is utime: either a USB connection exists or not a Pyboard
else:
    # Running on RTC timebase with no USB connection
```

# 4. rtc_time.py

This provides the following.

Variable:
 * `use_utime` `True` if the `uasyncio` timebase is `utime`, `False` if it is
 the RTC.

Functions:  
If the timebase is `utime` these are references to the corresponding `utime`
functions. Otherwise they are direct replacements but using the RTC as their
timebase. See the `utime` official documentation for these.  
 * `ticks_ms`
 * `ticks_add`
 * `ticks_diff`
 * `sleep_ms` This should not be used if the RTC timebase is in use as its
 usage of the RTC will conflict with the `lo_power` coro.

Coroutine:  
 * `lo_power` Argument: `t_ms`. This coro repeatedly issues `pyb.stop`, waking
 after `t_ms` ms. The higher `t_ms` is, the greater the latency experienced by
 other coros and by I/O. Smaller values may result in higher power consumption
 with other coros being scheduled more frequently.

# 5. Application design

Attention to detail is required to minimise power consumption, both in terms of
hardware and code.

## 5.1 Hardware

Hardware issues are covered [here](https://github.com/peterhinch/micropython-micropower).
To summarise an SD card consumes on the order of 150μA. For lowest power
consumption use the onboard flash memory. Peripherals usually consume power
even when not in use: consider switching their power source under program
control.

## 5.2 Application Code

Issuing `pyb.stop` directly in code is unwise; also, when using the RTC
timebase, calling `rtc_time.sleep_ms`. This is because there is only one RTC,
and hence there is potential conflict with different routines issuing
`rtc.wakeup`. The coro `rtc_time.lo_power` should be the only one issuing this
call.

The implications of the `t_ms` argument to `rtc_time.lo_power` should be
considered. During periods when the Pyboard is in a `stop` state, other coros
will not be scheduled. I/O from interrupt driven devices such as UARTs will be
buffered for processing when stream I/O is next scheduled. The size of buffers
needs to be determined in conjunction with data rates and with this latency
period.

Long values of `t_ms` will affect the minimum time delays which can be expected
of `await asyncio.sleep_ms`. Such values will affect the aggregate amount of
CPU time any coro will acquire. If `t_ms == 200` the coro

```python
async def foo():
    while True:
        # Do some processing
        await asyncio.sleep(0)
```

will execute (at best) at a rate of 5Hz. And possibly considerably less
frequently depending on the behaviour of competing coros. Likewise

```python
async def bar():
    while True:
        # Do some processing
        await asyncio.sleep_ms(10)
```

the 10ms sleep may be 200ms or longer, again dependent on other application
code.
