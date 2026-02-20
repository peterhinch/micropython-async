# asyncio_alt

This is a minimally modified version of `asyncio` with the objective of enabling
one or both of:
1. Reduced latency for I/O tasks including `ThreadSafeFlag`.
2. Reduced power consumption on platforms with effective lightsleep capability.

Usage and functionality are identical to standard. Some attention to detail is
required to take advantage of these added features. In particular the
availability and effectiveness of low power mode is platform dependent.

# 1. Installation

```bash
$ mpremote mip install github:peterhinch/micropython-async/v3/asyncio_alt
```
To install the `timer_test` and `tsf_test` demos issue
```bash
$ mpremote mip install github:peterhinch/micropython-async/v3/asyncio_alt/demos
```

# 2. Initialisation

To invoke priority I/O scheduling issue
```py
import asyncio_alt as asyncio
asyncio.roundrobin(False)  # Replace roundrobin scheduling with fast I/O
```
Issuing `roundrobin` without args returns the current value.  
For low power mode issue:
```py
import asyncio_alt as asyncio
asyncio.power_mode(True)  # Attempt to engage low power mode
```
This will raise a `ValueError` if the platform does not support the mode.
Issuing `.power_mode()` without args returns the current mode.

It is entirely valid to specify both modes. Mode selection should be done
immediately after import. Changing modes of a running system is not recommended.

# 3. Fast I/O mode

## 3.1 Latency performance

This may be tested with the following script:
```py
import timer_test
```
This implements a timer using the I/O mechanism as described in
[the tutorial](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#64-writing-streaming-device-drivers).
The demo runs the timer in the presence of ten tasks, each of which blocks for
5ms. Behaviour with roundrobin and fast I/O scheduling is demonstrated. On an
RP2350 a nominal 100ms timer measures 155ms with normal (roundrobin) scheduling
and ~102ms with fast I/O.

Using the official version the duration is around 155ms because each of the
pending tasks runs in roundrobin fashion before the I/O event is handled.

This tests `ThreadSafeFlag` latency:
```py
import tsf_test
```
These tests "cheat" slightly because they are triggered from an `asyncio` task.
If triggering were from a truly asynchronous source, latency of up to 5ms (the
blocking time of a task) would be expected.

## 3.2 Implications of prioritising I/O

Consider a system where a `ThreadSafeFlag` (TSF) is set by a hard interrupt
service routine (ISR). The task waiting on the TSF is scheduled for execution.
In standard `asyncio`, when the running task yields to the scheduler, all other
pending tasks will run, followed by the waiting task. In this version the
waiting task will run first. In systems with many pending tasks (e.g. tasks that
issue `await asyncio.sleep(0)`) there is a substantial reduction in latency.

By the same token, a `StreamReader` receiving data will be serviced more
promptly, reducing the need for buffering.

This comes with a potential cost. The design of `asyncio` based on round robin
scheduling ensures that no properly written task can permanently starve other
tasks of execution. Consider the following example:
```py
async def hazard():
    while True:
        await tsf.wait()  # Wait on a ThreadSafeFlag
        time.sleep_ms(20)  # Stand-in for code that takes 20ms to run
```
If the TSF was triggered at 50Hz, no other task would get to run. On official
`asyncio` all pending tasks would run, albeit at a risk that eventually the TSF
would be set twice before being serviced.

When running this version, consider the blocking time of any I/O tasks in the
context of the maximum rate at which the task might be triggered: I/O tasks
should be designed to run to completion (or to a yield) quickly.

# 4. Low power mode

Achieving low power consumption requires some attention to detail. The mode
works by invoking `machine.lightsleep` during periods when the scheduler is
waiting, either for I/O or for a task to become due. This has two consequences:
* Power saving can only be as good as that offered by `.lightsleep`.
* The application must ensure that there are times when the scheduler is waiting
on a task to be due.

Note that `lightsleep` power draw is often reduced when the USB interface is
unused or disabled, with the hardware powered from an external source.

## 4.1 Checking platform suitability

The low power suitability of a platform may be tested by pasting this script at
the REPL:
```py
from time import ticks_ms, ticks_diff
from machine import lightsleep
t = ticks_ms()
lightsleep(5000)
dt = ticks_diff(ticks_ms(), t)
print(dt)
```
The machine should pause for five seconds then print a value of approximately
5000. A value of ~0 indicates that the `ticks_ms` clock stops during light sleep
rendering the platform unsuitable. Currently STM32 (Pyboards) are in this
category. RP2040 and RP2350 work fine.

## 4.2 Implication of low power mode

This mode works as follows. Whenever there are no pending tasks (i.e. tasks
ready for execution) the scheduler polls the I/O system. Normally polling is
continuous. In low power mode it occurs at 20ms intervals, with the system
going into light sleep for those periods. In a system where all tasks wait on a
nonzero time, this can result in an order of magnitude reduction in power draw.

The following script was run on an RP2040 powered from a bench supply:
```py
import asyncio_alt as asyncio
from machine import Pin
asyncio.power_mode(True)

async def foo():
    p = Pin(16, Pin.OUT)
    x = 0
    while True:
        await asyncio.sleep(1)
        p(x)
        x ^= 1

asyncio.run(foo())
```
Current consumption averaged over 10s was 1.28mA vs 18mA.

Note that the benefit will be lost if any task does
```py
async def bar():
    while True:
        await asyncio.sleep(0)
        # synchronous code
```
This is because, even if all other tasks are waiting on a `sleep(t)`, `bar()`
will repeatedly be scheduled for execution. There will be no time while the
scheduler is paused waiting on I/O (I/O is polled, but for a minimal period),
so `lightsleep` does not run.

The I/O polling interval of 20ms was chosen based on measurements on RP2: a
longer period provided only marginal improvements in power draw.
