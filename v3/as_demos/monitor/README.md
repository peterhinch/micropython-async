# 1. A uasyncio monitor

This library provides a means of examining the behaviour of a running
`uasyncio` system. The device under test is linked to a Raspberry Pi Pico. The
latter displays the behaviour of the host by pin changes and/or optional print
statements. Communication with the Pico is uni-directional via a UART so only a
single GPIO pin is used - at last a use for the ESP8266 transmit-only UART(1).

A logic analyser or scope provides an insight into the way an asynchronous
application is working.

Where an application runs multiple concurrent tasks it can be difficult to
locate a task which is hogging CPU time. Long blocking periods can also result
from several tasks each of which can block for a period. If, on occasion, these
are scheduled in succession, the times can add. The monitor issues a trigger
when the blocking period exceeds a threshold. With a logic analyser the system
state at the time of the transient event may be examined.

The following image shows the `quick_test.py` code being monitored at the point
when a task hogs the CPU. The top line 00 shows the "hog detect" trigger. Line
02 shows the fast running `hog_detect` task which cannot run at the time of the
trigger. Lines 01 and 03 show the `foo` and `bar` tasks.  
![Image](/.monitor.jpg)

## 1.1 Pre-requisites

The device being monitored must run firmware V1.17 or later. The `uasyncio`
version should be V3 (as included in the firmware).

## 1.2 Usage

Example script `quick_test.py` provides a usage example.

An application to be monitored typically has the following setup code:
```python
from monitor import monitor, hog_detect, set_uart
set_uart(2)  # Define device under test UART no.
```

Coroutines to be monitored are prefixed with the `@monitor` decorator:
```python
@monitor(2, 3)
async def my_coro():
    # code
```
The decorator args are as follows:
 1. A unique `ident` for the code being monitored. Determines the pin number on
 the Pico. See [Pico Pin mapping](./README.md#3-pico-pin-mapping).
 2. An optional arg defining the maximum number of concurrent instances of the
 task to be independently monitored (default 1).

Whenever the code runs, a pin on the Pico will go high, and when the code
terminates it will go low. This enables the behaviour of the system to be
viewed on a logic analyser or via console output on the Pico. This behavior
works whether the code terminates normally, is cancelled or has a timeout.

In the example above, when `my_coro` starts, the pin defined by `ident==2`
(GPIO 4) will go high. When it ends, the pin will go low. If, while it is
running, a second instance of `my_coro` is launched, the next pin (GPIO 5) will
go high. Pins will go low when the relevant instance terminates, is cancelled,
or times out. If more instances are started than were specified to the
decorator, a warning will be printed on the host. All excess instances will be
associated with the final pin (`pins[ident + max_instances - 1]`) which will
only go low when all instances associated with that pin have terminated.

Consequently if `max_instances=1` and multiple instances are launched, a
warning will appear on the host; the pin will go high when the first instance
starts and will not go low until all have ended.

## 1.3 Detecting CPU hogging

A common cause of problems in asynchronous code is the case where a task blocks
for a period, hogging the CPU, stalling the scheduler and preventing other
tasks from running. Determining the task responsible can be difficult.

The pin state only indicates that the task is running. A pin state of 1 does
not imply CPU hogging. Thus
```python
@monitor(3)
async def long_time():
    await asyncio.sleep(30)
```
will cause the pin to go high for 30s, even though the task is consuming no
resources for that period.

To provide a clue about CPU hogging, a `hog_detect` coroutine is provided. This
has `ident=0` and, if used, is monitored on GPIO 2. It loops, yielding to the
scheduler. It will therefore be scheduled in round-robin fashion at speed. If
long gaps appear in the pulses on GPIO 2, other tasks are hogging the CPU.
Usage of this is optional. To use, issue
```python
import uasyncio as asyncio
from monitor import monitor, hog_detect
# code omitted
asyncio.create_task(hog_detect())
# code omitted
```
To aid in detecting the gaps in execution, the Pico code implements a timer.
This is retriggered by activity on `ident=0`. If it times out, a brief high
going pulse is produced on pin 28, along with the console message "Hog". The
pulse can be used to trigger a scope or logic analyser. The duration of the
timer may be adjusted - see [section 4](./README.md~4-the-pico-code).

# 2. Monitoring synchronous code

In general there are easier ways to debug synchronous code. However in the
context of a monitored asynchronous application there may be a need to view the
timing of synchronous code. Functions and methods may be monitored either in
the declaration via a decorator or when called via a context manager.

## 2.1 The mon_func decorator

This works as per the asynchronous decorator, but without the `max_instances`
arg. This will activate the GPIO associated with ident 20 for the duration of
every call to `sync_func()`:
```python
@mon_func(20)
def sync_func():
    pass
```

## 2.2 The mon_call context manager

This may be used to monitor a function only when called from specific points in
the code.
```python
def another_sync_func():
    pass

with mon_call(22):
    another_sync_func()
```

It is advisable not to use the context manager with a function having the
`mon_func` decorator. The pin and report behaviour is confusing.

# 3. Pico Pin mapping

The Pico GPIO numbers start at 2 to allow for UART(0) and also have a gap where
GPIO's are used for particular purposes. This is the mapping between `ident`
GPIO no. and Pico PCB pin, with the pins for the timer and the UART link also
identified:

| ident | GPIO | pin  |
|:-----:|:----:|:----:|
| uart  |   1  |   2  |
|   0   |   2  |   4  |
|   1   |   3  |   5  |
|   2   |   4  |   6  |
|   3   |   5  |   7  |
|   4   |   6  |   9  |
|   5   |   7  |  10  |
|   6   |   8  |  11  |
|   7   |   9  |  12  |
|   8   |  10  |  14  |
|   9   |  11  |  15  |
|  10   |  12  |  16  |
|  11   |  13  |  17  |
|  12   |  14  |  19  |
|  13   |  15  |  20  |
|  14   |  16  |  21  |
|  15   |  17  |  22  |
|  16   |  18  |  24  |
|  17   |  19  |  25  |
|  18   |  20  |  26  |
|  19   |  21  |  27  |
|  20   |  22  |  29  |
|  21   |  26  |  31  |
|  22   |  27  |  32  |
| timer |  28  |  34  |

The host's UART `txd` pin should be connected to Pico GPIO 1 (pin 2). There
must be a link between `Gnd` pins on the host and Pico.

# 4. The Pico code

Monitoring of the UART with default behaviour is started as follows:
```python
from monitor_pico import run
run()
```
By default the Pico does not produce console output and the timer has a period
of 100ms - pin 28 will pulse if ident 0 is inactive for over 100ms. These
behaviours can be modified by the following `run` args:
 1. `period=100` Define the timer period in ms.
 2. `verbose=()` Determines which `ident` values should produce console output.

Thus to run such that idents 4 and 7 produce console output, with hogging
reported if blocking is for more than 60ms, issue
```python
from monitor_pico import run
run(60, (4, 7))
```

# 5. Design notes

The use of decorators is intended to ease debugging: they are readily turned on
and off by commenting out.

The Pico was chosen for extremely low cost. It has plenty of GPIO pins and no
underlying OS to introduce timing uncertainties.

Symbols transmitted by the UART are printable ASCII characters to ease
debugging. A single byte protocol simplifies and speeds the Pico code.

The baudrate of 1Mbps was chosen to minimise latency (10μs per character is
fast in the context of uasyncio). It also ensures that tasks like `hog_detect`,
which can be scheduled at a high rate, can't overflow the UART buffer. The
1Mbps rate seems widely supported.
