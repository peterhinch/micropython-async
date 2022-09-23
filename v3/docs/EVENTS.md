# 1. An alternative to callbacks in uasyncio code

A hardware device like a pushbutton or a software object like an MQTT client
is designed to respond to an external asynchronous event. At the device driver
level there are two common approaches to handling this (see note below):
 1. The driver provides a method which blocks until the event occurs (e.g.
 [machine.uart.read][1r].
 2. The user specifies a callback function which runs when the event occurs
 (e.g.[umqtt.simple][2r]).

The first approach is incompatible with asynchronous code because the blocking
method stalls the scheduler while it is waiting. The second solves this because
the callback consumes no resources until the event actually occurs. However it
is not without problems. There is no standard way to specify callbacks, nor is
there a standard way to pass arguments to them or to retrieve a result. Further
a user might want to launch a task rather than run a synchronous callback. All
these problems can be solved, but solutions are _ad hoc_ and will vary between
drivers.

For example, `umqtt.simple` has a `set_callback` method with no way to pass
args. Other drivers will require the callback (and perhaps args) to be passed
as a constructor arg. Some drivers provide a method enabling the callback's
result to be retrieved.

Further, if a requirement has logic such as to "send a message if event A
is followed by either event B or event C" you are likely to find yourself at
the gates of a place commonly known as "callback hell".

The one merit of designing callbacks into drivers is that it enables users to
access `uasyncio` code with purely synchronous code. Typical examples are GUIs
such as [micro-gui][1m]). These application frameworks use asynchronous code
internally but may be accessed with conventional synchronous code.

For asynchronous programmers the API's of drivers, and their internal logic,
can be simplified by abandoning callbacks in favour of `Event` beaviour. In
essence the driver might expose an `Event` instance or be designed to emulate
an `Event`. No capability is lost because the application can launch a callback
or task when the `Event` is set. With the design approach outlined below, the
need for callbacks is much reduced.

Note the `Stream` mechanism provides another approach which works well with
devices such as sockets and UARTs. It is less well suited to handling arbitrary
events, partly because it relies on polling under the hood.

# 2. Rationale

Consider a device driver `Sensor` which has a bound `Event` object `.ready`.
An application might run a task of form:
```python
async def process_sensor():
    while True:
        await sensor.ready.wait()
        sensor.ready.clear()
        # Read and process sensor data
```
Note that the action taken might be to run a callback or to launch a task:
```python
async def process_sensor():
    while True:
        await sensor.ready.wait()
        sensor.ready.clear()
        result = callback(args)
        asyncio.create_task(sensor_coro(args))
```
An `Event` interface allows callback-based code and makes straightforward the
passing of arguments and retrieval of return values. However it also enables a
progrmming style that largely eliminates callbacks. Note that all you need to
know to access this driver interface is the name of the bound `Event`.

This doc aims to demostrate that the event based approach can simplify
application logic by eliminating the need for callbacks.

The design of `uasyncio` V3 and its `Event` class enables this approach
because:
 1. A task waiting on an `Event` is put on a queue where it consumes no CPU
 cycles until the event is triggered.
 2. The design of `uasyncio` can support large numbers of tasks (hundreds) on
 a typical microcontroller. Proliferation of tasks is not a problem, especially
 where they are small and spend most of the time paused waiting on queues.

This contrasts with other schedulers (such as `uasyncio` V2) where there was no
built-in `Event` class; typical `Event` implementations used polling and were
convenience objects rather than performance solutions.

The `Event` class `.clear` method provides additional flexibility relative to
callbacks:
 1. An `Event` can be cleared immediately after being set; if multiple tasks
 are waiting on `.wait()`, all will resume running.
 2. Alternatively the `Event` may be cleared later. The timing of clearing the
 `Event` determines its behaviour if, at the time when the `Event` is set, a
 task waiting on the `await event.wait()` statement has not yet reached it. If
 execution reaches `.wait()` before the `Event` is cleared, it will not pause.
 If the `Event` is cleared, it will pause until it is set again.

# 3. Device driver design

This document introduces the idea of an event-like object (ELO). This is an
object which may be used in place of an `Event` in program code. An ELO must
expose a `.wait` asynchronous method which will pause until an event occurs.
Additionally it can include `.clear` and/or `.set`. A device driver may become
an ELO by implementing `.wait` or by subclassing `Event` or `ThreadSafeFlag`.
Alternatively a driver may expose one or more bound `Event` or ELO instances.

ELO examples are:

| Object               | wait | clear | set | comments          |
|:---------------------|:----:|:-----:|:---:|:------------------|
| [Event][4m]          | Y    | Y     | Y   |                   |
| [ThreadSafeFlag][3m] | Y    | N     | Y   | Self-clearing     |
| [Message][7m]        | Y    | N     | Y   | Subclass of above |
| [Delay_ms][2m]       | Y    | Y     | Y   | Self-setting      |
| WaitAll              | Y    | Y     | N   | See below         |
| WaitAny              | Y    | Y     | N   |                   |

Drivers exposing `Event` instances include:

 * [ESwitch](./EVENTS.md#61-eswitch) Micro debounced interface to a switch.
 * [EButton](./EVENTS.md#62-ebutton) Micro debounced interface to a pushbutton.
 * [Switch][5m] Similar but interfaces also expose callbacks.
 * [Pushbutton][6m]

# 4. Primitives

Applying `Events` to typical logic problems requires two new primitives:
`WaitAny` and `WaitAll`. Each is an ELO. These primitives may be cancelled or
subject to a timeout with `uasyncio.wait_for()`, although judicious use of
`Delay_ms` offers greater flexibility than `wait_for`.

## 4.1 WaitAny

The constructor takes an iterable of ELO's. Its `.wait` method pauses until the
first of the ELO's is set; the method returns the object that triggered it,
enabling the application code to determine the reason for its triggering.

The last ELO to trigger a `WaitAny` instance may also be retrieved by issuing
the instance's `.event()` method.
```python
from primitives import WaitAny
async def foo(elo1, elo2)
    evt = WaitAny((elo1, elo2)).wait()
    if evt is elo1:
        # Handle elo1
```
`WaitAny` has a `clear` method which issues `.clear()` to all passed ELO's with
a `.clear` method.

## 4.2 WaitAll

The constructor takes an iterable of ELO's. Its `.wait` method pauses until all
of the ELO's is set.

`WaitAll` has a `clear` method which issues `.clear()` to all passed ELO's with
a `.clear` method.

## 4.3 Nesting

The fact that these primitives are ELO's enables nesting:
```Python
await WaitAll((event1, event2, WaitAny(event3, event4))).wait()
```
This will pause until `event1` and `event2` and either `event3`or `event4` have
been set.

# 5. Event based programming

## 5.1 Use of Delay_ms

The [Delay_ms class](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#38-delay_ms-class)
is an ELO and can be used as an alternative to `asyncio.wait_for`: it has the
advantage that it can be retriggered. It can also be stopped or its duration
changed dynamically. In the following sample `task_a` waits on an `Event` but
it also aborts if `task_b` stops running for any reason:
```python
from primitives import Delay_ms, WaitAny
delay = Delay_ms(duration=1000)
async def task_b():
    while True:
        delay.trigger()  # Keep task_a alive
        # do some work
        await asyncio.sleep_ms(0)

async def task_a(evt):  # Called with an event to wait on
    while True:
        cause = await WaitAny((evt, delay)).wait()
        if cause is delay:  # task_b has ended
            delay.clear()  # Clear the Event
            return  # Abandon the task
        # Event has occurred
        evt.clear()
        # Do some work
        await asyncio.sleep_ms(0)
```
## 5.2 Long and very long button press

A user had a need to distinguish short, fairly long, and very long presses of a
pushbutton. There was no requirement to detect double clicks, so the minimal
`ESwitch` driver was used.

This solution does not attempt to disambiguate the press events: if a very long
press occurs, the short press code will run, followed by the "fairly long"
code, and then much later by the "very long" code. Disambiguating implies first
waiting for button release and then determining which application code to run:
in the application this delay was unacceptable.
```python
async def main():
    btn = ESwitch(Pin('X17', Pin.IN, Pin.PULL_UP), lopen=0)
    ntim = Delay_ms(duration = 1000)  # Fairly long press
    ltim = Delay_ms(duration = 8000)  # Very long press
    while True:
        ltim.stop()  # Stop any running timers and clear their event
        ntim.stop()
        await btn.close.wait()
        btn.close.clear()
        ntim.trigger()  # Button pressed, start timers, await release
        ltim.trigger()  # Run any press code
        ev = await WaitAny((btn.open, ntim)).wait()
        if ev is btn.open:
            # Run "short press" application code
        else:  # ev is ntim: Fairly long timer timed out
            # Run "fairly long" application code
            # then check for very long press
            ev = await WaitAny((btn.open, ltim)).wait()
            if ev is ltim:  # Long timer timed out
                # Run "very long" application code
        # We have not cleared the .open Event, so if the switch is already open
        # there will be no delay below. Otherwise we await realease.
        # Must await release otherwise the event is cleared before release
        # occurs, setting the release event before the next press event.
        await btn.open.wait()
        btn.open.clear()
```
Disambiguated version. Wait for button release and decide what to do based on
which timers are still running:
```python
async def main():
    btn = ESwitch(Pin('X17', Pin.IN, Pin.PULL_UP), lopen=0)
    ntim = Delay_ms(duration=1000)  # Fairly long press
    ltim = Delay_ms(duration=8000)  # Very long press
    while True:
        ltim.stop()  # Stop any running timers and clear their event
        ntim.stop()
        await btn.close.wait()
        btn.close.clear()
        ntim.trigger()  # Button pressed, start timers, await release
        ltim.trigger()  # Run any press code
        await btn.open.wait()
        btn.open.clear()
        # Button released: check for any running timers
        if not ltim():  # Very long press timer timed out before button was released
            # Run "Very long" code
        elif not ntim():
            # Run "Fairly long" code
        else:
            # Both timers running: run "short press" code
```

## 5.3 Application example

A measuring instrument is started by pressing a button. The measurement
normally runs for five seconds. If the sensor does not detect anything, the
test runs until it does, however it is abandoned if nothing has been detected
after a minute. While running, extra button presses are ignored. During a
normal five second run, extra detections from the sensor are ignored.

This can readily be coded using callbacks and synchronous or asynchronous code,
however the outcome is likely to have a fair amount of _ad hoc_ logic.

This event based solution is arguably clearer to read:
```python
from primitives import EButton, WaitAll, Delay_ms
btn = EButton(args)  # Has Events for press, release, double, long
bp = btn.press
sn = Sensor(args)  # Assumed to have an Event interface.
tm = Delay_ms(duration=5_000)  # Exposes .wait and .clear only.
events = (sn, tm)
async def foo():
    while True:
        bp.clear()  # Ignore prior button press
        await bp.wait()  # Button pressed
        events.clear()  # Ignore events that were set prior to this moment
        tm.trigger()  # Start 5 second timer
        try:
            await asyncio.wait_for(WaitAll(events).wait(), 60)
        except asyncio.TimeoutError:
            print("No reading from sensor")
        else:
            # Normal outcome, process readings
```

# 6. Drivers

This document describes drivers for mechanical switches and pushbuttons. These
have event based interfaces exclusively and support debouncing. The drivers are
simplified alternatives for 
[Switch](https://github.com/peterhinch/micropython-async/blob/master/v3/primitives/switch.py)
and [Pushbutton](https://github.com/peterhinch/micropython-async/blob/master/v3/primitives/pushbutton.py),
which also support callbacks.

## 6.1 ESwitch

This provides a debounced interface to a switch connected to gnd or to 3V3. A
pullup or pull down resistor should be supplied to ensure a valid logic level
when the switch is open. The default constructor arg `lopen=1` is for a switch
connected between the pin and gnd, with a pullup to 3V3. Typically the pullup
is internal, the pin being as follows:
```python
from machine import Pin
pin_id = 0  # Depends on hardware
pin = Pin(pin_id, Pin.IN, Pin.PULL_UP)
```
Constructor arguments:

 1. `pin` The Pin instance: should be initialised as an input with a pullup or
 down as appropriate.
 2. `lopen=1` Electrical level when switch is open circuit i.e. 1 is 3.3V, 0 is
 gnd.
 
Methods:

 1. `__call__` Call syntax e.g. `myswitch()` returns the logical debounced
 state of the switch i.e. 0 if open, 1 if closed.
 2. `deinit` No args. Cancels the polling task and clears bound `Event`s.

Bound objects:
 1. `debounce_ms` An `int`. Debounce time in ms. Default 50.
 2. `close` An `Event` instance. Set on contact closure.
 3. `open` An `Event` instance. Set on contact open.

Application code is responsible for clearing the `Event` instances.

## 6.2 EButton
 
This extends the functionality of `ESwitch` to provide additional events for
long and double presses.

This can support normally open or normally closed switches, connected to `gnd`
(with a pullup) or to `3V3` (with a pull-down). The `Pin` object should be
initialised appropriately. The default state of the switch can be passed in the
optional "sense" parameter on the constructor, otherwise the assumption is that
on instantiation the button is not pressed.

The Pushbutton class uses logical rather than physical state: a button's state
is considered `True` if pressed, otherwise `False` regardless of its physical
implementation.

Constructor arguments:

 1. `pin` Mandatory. The initialised Pin instance.
 2. `suppress` Default `False`. See [section 6.2.1](./EVENTS.md#621-the-suppress-constructor-argument).
 3. `sense` Default `None`. Optionally define the electrical connection: see
 [section 6.2.2](./EVENTS.md#622-the-sense-constructor-argument)

Methods:

 1. `__call__` Call syntax e.g. `mybutton()` Returns the logical debounced
 state of the button (`True` corresponds to pressed).
 2. `rawstate()` Returns the logical instantaneous state of the button. There
 is probably no reason to use this.
 3. `deinit` No args. Cancels the running task and clears all events.

Bound `Event`s:

 1. `press` Set on button press.
 2. `release` Set on button release.
 3. `long` Set if button press is longer than `EButton.long_press_ms`.
 4. `double` Set if two button preses occur within `EButton.double_click_ms`.

Application code is responsible for clearing these `Event`s

Class attributes:
 1. `debounce_ms` Debounce time in ms. Default 50.
 2. `long_press_ms` Threshold time in ms for a long press. Default 1000.
 3. `double_click_ms` Threshold time in ms for a double-click. Default 400.

### 6.2.1 The suppress constructor argument

Consider a button double-click. By default with `suppress=False` this will set
the bound `Event` instances in order, as follows:

 * `press`
 * `release`
 * `press`
 * `release`
 * `double`

Similarly a long press will trigger `press`, `long` and `release` in that
order. Some
applications may require only a single `Event` to be triggered. Setting
`suppress=True` ensures this. Outcomes are as follows:

| Occurence    | Events set      | Time of pimary event         |
|:-------------|:----------------|:-----------------------------|
| Short press  | press, release  | After `.double_click_ms`     |
| Double press | double, release | When the second press occurs |
| Long press   | long, release   | After `long_press_ms`        |

The tradeoff is that the `press` and `release` events are delayed: the soonest
it is possible to detect the lack of a double click is `.double_click_ms`ms
after a short button press. Hence in the case of a short press when `suppress`
is `True`, `press` and `release` events are set on expiration of the double
click timer.

### 6.2.2 The sense constructor argument

In most applications it can be assumed that, at power-up, pushbuttons are not
pressed. The default `None` value uses this assumption to read the pin state
and to assign the result to the `False` (not pressed) state at power up. This
works with normally open or normally closed buttons wired to either supply
rail; this without programmer intervention.

In certain use cases this assumption does not hold, and `sense` must explicitly
be specified. This defines the logical state of the un-pressed button. Hence
`sense=0` defines a button connected in such a way that when it is not pressed,
the voltage on the pin is gnd.

Whenever the pin value changes, the new value is compared with `sense` to
determine whether the button is closed or open.

# Appendix 1 Polling

The primitives or drivers referenced here do not use polling with the following
exceptions:
 1. Switch and pushbutton drivers. These poll the `Pin` instance for electrical
 reasons described below. 
 2. `ThreadSafeFlag` and subclass `Message`: these use the stream mechanism.

Other drivers and primitives are designed such that paused tasks are waiting on
queues and are therefore using no CPU cycles.

[This reference][1e] states that bouncing contacts can assume invalid logic
levels for a period. It is a reaonable assumption that `Pin.value()` always
returns 0 or 1: the drivers are designed to cope with any sequence of such
readings. By contrast, the behaviour of IRQ's under such conditions may be
abnormal. It would be hard to prove that IRQ's could never be missed, across
all platforms and input conditions.

Pin polling aims to use minimal resources, the main overhead being `uasyncio`'s
task switching overhead: typically about 250 μs. The default polling interval
is 50 ms giving an overhead of ~0.5%.


[1m]: https://github.com/peterhinch/micropython-micro-gui
[2m]: https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#38-delay_ms-class

[3m]: https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#36-threadsafeflag
[4m]: https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#32-event
[5m]: https://github.com/peterhinch/micropython-async/blob/master/v3/docs/DRIVERS.md#31-switch-class
[6m]: https://github.com/peterhinch/micropython-async/blob/master/v3/docs/DRIVERS.md#41-pushbutton-class
[7m]: https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#39-message

[1r]: http://docs.micropython.org/en/latest/library/machine.UART.html#machine.UART.read
[2r]: https://github.com/micropython/micropython-lib/blob/ad9309b669cd4474bcd4bc0a67a630173222dbec/micropython/umqtt.simple/umqtt/simple.py

[1e]: http://www.ganssle.com/debouncing.htm
