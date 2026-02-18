# asyncio_alt

This is a very lightly modified version of `asyncio` with two objectives:
1. Reduced latency for I/O tasks including `ThreadSafeFlag`.
2. Reduced power consumption on platforms with effective lightsleep capability.

Usage and functionality are identical to standard. Some attention to detail is
required to take advantage of these features. In particular the availability and
effectiveness of low power mode is platform dependent.

# Installation

```bash
$ mpremote mip install github:peterhinch/micropython-async/v3/asyncio_alt
```
Programs using this version should run
```py
import asyncio_alt as asyncio
```

# Usage

Reduced latency mode is always present. Low power mode must be specifically
engaged:
```py
import asyncio_alt as asyncio
asyncio.power_mode(True)  # Attempt to engage low power mode
```
This will raise a `ValueError` if the platform does not support the mode.
Issuing `.power_mode()` without args returns the current mode.

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
rendering the machine unsuitable.

# Latency performance

This may be tested with the following script:
```py
import asyncio_alt.demos.timer_test
```
This implements a timer using the I/O mechanism as described in
[the tutorial](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#64-writing-streaming-device-drivers).
The demo runs the timer in the presence of ten tasks, each of which blocks for
5ms. The duration of a nominal 100ms delay is measured. Using this version on
RP2350 it measures around 102ms. Using the official version the duration is
around 155ms because each of the pending tasks runs before the I/O event is
handled.

# Implications of prioritising I/O

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
context of the maximum rate at which the task might be triggered.

# Implication of low power mode

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
