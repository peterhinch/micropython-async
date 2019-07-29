# fast_io: A modified version of uasyncio

This version is a "drop in" replacement for official `uasyncio`. Existing
applications should run under it unchanged and with essentially identical
performance except that task cancellation and timeouts are expedited "soon"
rather than being deferred until the task is next scheduled.

"Priority" features are only enabled if the event loop is instantiated with
specific arguments.

This version has the following features relative to official V2.0:
 * Timeouts and task cancellation are handled promptly, rather than being
 deferred until the coroutine is next scheduled.
 * I/O can optionally be handled at a higher priority than other coroutines
 [PR287](https://github.com/micropython/micropython-lib/pull/287).
 * Tasks can yield with low priority, running when nothing else is pending.
 * Callbacks can similarly be scheduled with low priority. 
 * A [bug](https://github.com/micropython/micropython/pull/3836#issuecomment-397317408)
 whereby bidirectional devices such as UARTS can fail to handle concurrent
 input and output is fixed.
 * It is compatible with `rtc_time.py` for micro-power applications documented
 [here](./lowpower/README.md). This is a Pyboard-only extension (including
 Pyboard D).
 * An assertion failure is produced if `create_task` or `run_until_complete`
 is called with a generator function
 [PR292](https://github.com/micropython/micropython-lib/pull/292). This traps
 a common coding error which otherwise results in silent failure.
 * The presence and version of the `fast_io` version can be tested at runtime.
 * The presence of an event loop instance can be tested at runtime.
 * `run_until_complete(coro())` now returns the value returned by `coro()` as
 per CPython
 [micropython-lib PR270](https://github.com/micropython/micropython-lib/pull/270).
 * The `StreamReader` class now has a `readinto(buf, n=0)` method to enable
 allocations to be reduced.

Note that priority device drivers are written by using the officially supported
technique for writing stream I/O drivers. Code using such drivers will run
unchanged under the `fast_io` version. Using the fast I/O mechanism requires
adding just one line of code. This implies that if official `uasyncio` acquires
a means of prioritising I/O other than that in this version, application code
changes should be minimal. 

#### Changes incompatible with prior versions

V0.24  
The `version` bound variable now returns a 2-tuple.

Prior versions.  
The high priority mechanism formerly provided in `asyncio_priority.py` was a
workround based on the view that stream I/O written in Python would remain
unsupported. This is now available so `asyncio_priority.py` is obsolete and
should be deleted from your system. The facility for low priority coros
formerly provided by `asyncio_priority.py` is now implemented.

###### [Main README](./README.md)

# Contents

 1. [Installation](./FASTPOLL.md#1-installation)  
  1.1 [Benchmarks](./FASTPOLL.md#11-benchmarks) Benchmark and demo programs.  
 2. [Rationale](./FASTPOLL.md#2-rationale)  
  2.1 [Latency](./FASTPOLL.md#21-latency)  
  2.2 [Timing accuracy](./FASTPOLL.md#22-timing-accuracy)  
  2.3 [Polling in uasyncio](./FASTPOLL.md#23-polling-in-usayncio)  
 3. [The modified version](./FASTPOLL.md#3-the-modified-version)  
  3.1 [Fast IO](./FASTPOLL.md#31-fast-io)  
  3.2 [Low Priority](./FASTPOLL.md#32-low-priority)  
  3.3 [Other Features](./FASTPOLL.md#33-other-features)  
   3.3.1 [Version](./FASTPOLL.md#331-version)  
   3.3.2 [Check event loop status](./FASTPOLL.md#332-check-event-loop-status)  
   3.3.3 [StreamReader readinto method](./FASTPOLL.md#333-streamreader-readinto-method)  
  3.4 [Low priority yield](./FASTPOLL.md#34-low-priority-yield)  
   3.4.1 [Task Cancellation and Timeouts](./FASTPOLL.md#341-task-cancellation-and-timeouts)  
  3.5 [Low priority callbacks](./FASTPOLL.md#35-low-priority-callbacks)  
 4. [ESP Platforms](./FASTPOLL.md#4-esp-platforms)  
 5. [Background](./FASTPOLL.md#4-background)  
 6. [Performance](./FASTPOLL.md#6-performance)

# 1. Installation

The basic approach is to install and test `uasyncio` on the target hardware.
Replace `core.py` and `__init__.py` with the files in the `fast_io` directory.

The current MicroPython release build (1.10) has `uasyncio` implemented as a
frozen module. The following options for installing `fast_io` exist:

 1. Use a daily build, install `uasyncio` as per the tutorial then replace the
 above files.
 2. Build the firmware with the `fast_io` version implemented as frozen
 bytecode.
 3. Use a release build. Install as in 1. above. Then change the module search
 order by modifying `sys.path`. The initial entry `''` specifies frozen
 bytecode. If this is deleted and appended to the end, frozen files will only
 be found if there is no match in the filesystem.

```python
import sys
sys.path.append(sys.path.pop(0))  # Prefer modules in filesystem
```

See [ESP Platforms](./FASTPOLL.md#6-esp-platforms) for general comments on the
suitability of ESP platforms for systems requiring fast response.

## 1.1 Benchmarks

The following files demonstrate the performance gains offered by prioritisation
and the improvements to task cancellation and timeouts. They also show the use
of these features. Documentation is in the code.

Tests and benchmarks to run against the official and `fast_io` versions:
 * `benchmarks/latency.py` Shows the effect on latency with and without low
 priority usage.
 * `benchmarks/rate.py` Shows the frequency with which uasyncio schedules
 minimal coroutines (coros).
 * `benchmarks/rate_esp.py` As above for ESP32 and ESP8266.
 * `fast_io/ms_timer.py` An I/O device driver providing a timer with higher
 precision timing than `wait_ms()` when run under the `fast_io` version.
 * `fast_io/ms_timer_test.py` Test/demo program for above.
 * `fast_io/pin_cb.py` An I/O device driver which causes a pin state change to
 trigger a callback. This is a driver, not an executable test program.
 * `fast_io/pin_cb_test.py` Demo of above driver: illustrates performance gain
 under `fast_io`.

Tests requiring the current version of the `fast_io` fork:
 * `benchmarks/rate_fastio.py` Measures the rate at which coros can be scheduled
 if the fast I/O mechanism is used but no I/O is pending.
 * `benchmarks/call_lp.py` Demo of low priority callbacks.
 * `benchmarks/overdue.py` Demo of maximum overdue feature.
 * `benchmarks/priority_test.py` Cancellation of low priority coros.
 * `fast_io/fast_can_test.py` Demo of cancellation of paused tasks.
 * `fast_io/iorw_can.py` Cancellation of task waiting on I/O.
 * `fast_io/iorw_to.py` Timeouts applies to tasks waiting on I/O.

# 2. Rationale

MicroPython firmware now enables device drivers for stream devices to be
written in Python, via `uio.IOBase`. This mechanism can be applied to any
situation where a piece of hardware or an asynchronously set flag needs to be
polled. Such polling is efficient because it is handled in C using
`select.poll`, and because the coroutine accessing the device is descheduled
until polling succeeds.

Unfortunately official `uasyncio` polls I/O with a relatively high degree of
latency.

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

The variant also enables coros to yield control in a way which prevents them
from competing with coros which are ready for execution. Coros which have
yielded in a low priority fashion will not be scheduled until all "normal"
coros are waiting on a nonzero timeout. The benchmarks show that the
improvement in the accuracy of time delays can exceed two orders of magnitude.

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

Alternatively this latency may be reduced by enabling the `foo()` instances to
yield in a low priority manner. In the case where all coros other than
`handle_isr()` are low priority the latency is reduced to 300μs - a figure
of about double the inherent latency of uasyncio.

The benchmark latency.py demonstrates this. Documentation is in the code; it
can be run against both official and priority versions. This measures scheduler
latency. Maximum application latency, measured relative to the incidence of an
asynchronous event, will be 300μs plus the worst-case delay between yields of
any one competing task.

### 2.1.1 I/O latency

The official version of `uasyncio` has even higher levels of latency for I/O
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

Practical cases exist where the `foo()` tasks are not time-critical: in such
cases the performance of time critical tasks may be enhanced by enabling
`foo()` to submit for rescheduling in a way which does not compete with tasks
requiring a fast response. In essence "slow" operations tolerate longer latency
and longer time delays so that fast operations meet their performance targets.
Examples are:

 * User interface code. A system with ten pushbuttons might have a coro running
 on each. A GUI touch detector coro needs to check a touch against sequence of
 objects. Both may tolerate 100ms of latency before users notice any lag.
 * Networking code: a latency of 100ms may be dwarfed by that of the network.
 * Mathematical code: there are cases where time consuming calculations may
 take place which are tolerant of delays. Examples are statistical analysis,
 sensor fusion and astronomical calculations.
 * Data logging.

###### [Contents](./FASTPOLL.md#contents)

# 3. The modified version

The `fast_io` version adds `ioq_len=0` and `lp_len=0` arguments to
`get_event_loop`. These determine the lengths of I/O and low priority queues.
The zero defaults cause the queues not to be instantiated, in which case the
scheduler operates as per the official version. If an I/O queue length > 0 is
provided, I/O performed by `StreamReader` and `StreamWriter` objects is
prioritised over other coros. If a low priority queue length > 0 is specified,
tasks have an option to yield in such a way to minimise their competition with
other tasks.

Arguments to `get_event_loop()`:  
 1. `runq_len=16` Length of normal queue. Default 16 tasks.
 2. `waitq_len=16` Length of wait queue.
 3. `ioq_len=0` Length of I/O queue. Default: no queue is created.
 4. `lp_len=0` Length of low priority queue. Default: no queue.

###### [Contents](./FASTPOLL.md#contents)

## 3.1 Fast IO

Device drivers which are to be capable of running at high priority should be
written to use stream I/O: see
[Writing streaming device drivers](./TUTORIAL.md#64-writing-streaming-device-drivers).

The `fast_io` version will schedule I/O whenever the `ioctl` reports a ready
status. This implies that devices which become ready very soon after being
serviced can hog execution. This is analogous to the case where an interrupt
service routine is called at an excessive frequency.

This behaviour may be desired where short bursts of fast data are handled.
Otherwise drivers of such hardware should be designed to avoid hogging, using
techniques like buffering or timing.

###### [Contents](./FASTPOLL.md#contents)

## 3.2 Low Priority

The low priority solution is based on the notion of "after" implying a time
delay which can be expected to be less precise than the asyncio standard calls.
The `fast_io` version adds the following awaitable instances:

 * `after(t)`  Low priority version of `sleep(t)`.
 * `after_ms(t)`  Low priority version of `sleep_ms(t)`.

It adds the following event loop methods:

 * `loop.call_after(t, callback, *args)`
 * `loop.call_after_ms(t, callback, *args)`
 * `loop.max_overdue_ms(t=None)` This sets the maximum time a low priority task
 will wait before being  scheduled. A value of 0 corresponds to no limit. The
 default arg `None` leaves the period unchanged. Always returns the period
 value. If there is no limit and a competing task runs a loop with a zero delay
 yield, the low priority yield will be postponed indefinitely.

See [Low priority callbacks](./FASTPOLL.md#35-low-priority-callbacks)

###### [Contents](./FASTPOLL.md#contents)

## 3.3 Other Features

### 3.3.1 Version

Variable:  
 * `version` Returns a 2-tuple. Current contents ('fast_io', '0.25'). Enables
 the presence and realease state of this version to be determined at runtime.

### 3.3.2 Check event loop status

The way `uasyncio` works can lead to subtle bugs. The first call to
`get_event_loop` instantiates the event loop and determines the size of its
queues. Hence the following code will not behave as expected:
```python
import uasyncio as asyncio
bar = Bar()  # Constructor calls get_event_loop()
# and renders these args inoperative
loop = asyncio.get_event_loop(runq_len=40, waitq_len=40)
```
CPython V3.7 provides a function `get_running_loop` which enables the current
loop to be retrieved, raising a `RuntimeError` if one has not been
instantiated. This is provided in `fast_io`. In the above sample the `Bar`
constructor can call `get_running_loop` to avoid inadvertently instantiating an
event loop with default args.

Function:
 * `get_running_loop` No arg. Returns the event loop or raises a `RuntimeError`
 if one has not been instantiated.

Function:
 * `got_event_loop()` No arg. Returns a `bool`: `True` if the event loop has
 been instantiated. This is retained for compatibility: `get_running_loop` is
 preferred.

### 3.3.3 StreamReader readinto method

The purpose of this asynchronous method is to be a non-allocating complement to
the `StreamReader.read` method, enabling data to be read into a pre-existing
buffer. It assumes that the device driver providing the data has a `readinto`
method.

`StreamReader.readinto(buf, n=0)` args:  
`buf` the buffer to read into.  
`n=0` the maximum number of bytes to read - default the buffer size.

The method will pause (allowing other coros to run) until data is available.

Available data will be placed in the buffer. The return value is the number of
bytes read. The default maximum number of bytes is limited to the buffer size,
otherwise to the value of `n`.

This method calls the synchronous `readinto` method of the data source. This
may take one arg (the buffer) or two (the buffer followed by the maximum number
of bytes to read). If `StreamReader.readinto` is launched with a single arg,
the `readinto` method will receive that one arg.

It is the reponsibility of the device `readinto` method to validate the args,
to populate the buffer and to return the number of bytes read. It should return
"immediately" with as much data as is available. It will only be called when
the `ioctl` method indicates that read data is ready.

###### [Contents](./FASTPOLL.md#contents)

## 3.4 Low priority yield

Consider this code fragment:

```python
import uasyncio as asyncio
loop = asyncio.get_event_loop(lp_len=16)

async def foo():
    while True:
        # Do something
        await asyncio.after(1.5)  # Wait a minimum of 1.5s
        # code
        await asyncio.after_ms(20)  # Wait a minimum of 20ms
```

These `await` statements cause the coro to suspend execution for the minimum
time specified. Low priority coros run in a mutually "fair" round-robin fashion.
By default the coro will only be rescheduled when all "normal" coros are waiting
on a nonzero time delay. A "normal" coro is one that has yielded by any other
means.

This behaviour can be overridden to limit the degree to which they can become
overdue. For the reasoning behind this consider this code:

```python
import uasyncio as asyncio
loop = asyncio.get_event_loop(lp_len=16)

async def foo():
    while True:
        # Do something
        await asyncio.after(0)
```

By default a coro yielding in this way will be re-scheduled only when there are
no "normal" coros ready for execution i.e. when all are waiting on a nonzero
delay. The implication of having this degree of control is that if a coro
issues:

```python
while True:
    await asyncio.sleep(0)
    # Do something which does not yield to the scheduler
```

low priority tasks will never be executed. Normal coros must sometimes wait on
a non-zero delay to enable the low priority ones to be scheduled. This is
analogous to running an infinite loop without yielding.

This behaviour can be modified by issuing:

```python
loop = asyncio.get_event_loop(lp_len = 16)
loop.max_overdue_ms(1000)
```

In this instance a task which has yielded in a low priority manner will be
rescheduled in the presence of pending "normal" tasks if they cause a low
priority task to become overdue by more than 1s.

### 3.4.1 Task Cancellation and Timeouts

Tasks which yield in a low priority manner may be subject to timeouts or be
cancelled in the same way as normal tasks. See [Task cancellation](./TUTORIAL.md#521-task-cancellation)
and [Coroutines with timeouts](./TUTORIAL.md#522-coroutines-with-timeouts).

###### [Contents](./FASTPOLL.md#contents)

## 3.5 Low priority callbacks

The following `EventLoop` methods enable callback functions to be scheduled
to run when all normal coros are waiting on a delay or when `max_overdue_ms`
has elapsed:

`call_after(delay, callback, *args)` Schedule a callback with low priority.
Positional args:  
 1. `delay`  Minimum delay in seconds. May be a float or integer.
 2. `callback` The callback to run.
 3. `*args` Optional comma-separated positional args for the callback.

The delay specifies a minimum period before the callback will run and may have
a value of 0. The period may be extended depending on other high and low
priority tasks which are pending execution.

A simple demo of this is `benchmarks/call_lp.py`. Documentation is in the
code.

`call_after_ms(delay, callback, *args)` Call with low priority. Positional
args:  
 1. `delay` Integer. Minimum delay in millisecs before callback runs.
 2. `callback` The callback to run.
 3. `*args` Optional positional args for the callback.

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

# 6. Performance

The `fast_io` version is designed to enable existing applications to run
unchanged and to minimise the effect on raw scheduler performance in cases
where the priority functionality is unused.

The benchmark `rate.py` measures the rate at which tasks can be scheduled;
`rate_fastio` is identical except it instantiates an I/O queue and a low
priority queue. The benchmarks were run on a Pyboard V1.1 under official
`uasyncio` V2 and under the current `fast_io` version V0.24. Results were as
follows:

| Script | Uasyncio version | Period (100 coros) | Overhead | PBD |
|:------:|:----------------:|:------------------:|:--------:|:---:|
| rate | Official V2 | 156μs | 0% | 123μs |
| rate | fast_io | 162μs | 3.4% | 129μs |
| rate_fastio | fast_io | 206μs | 32% | 181μs |

The last column shows times from a Pyboard D SF2W.

If an I/O queue is instantiated I/O is polled on every scheduler iteration
(that is its purpose). Consequently there is a significant overhead. In
practice the overhead will increase with the number of I/O devices being
polled and will be determined by the efficiency of their `ioctl` methods.

Timings for current `fast_io` V0.24 and the original version were identical.
