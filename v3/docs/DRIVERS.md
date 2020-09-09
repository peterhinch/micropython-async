# 0. Introduction

Drivers for switches and pushbuttons are provided, plus a retriggerable delay
class. The switch and button drivers support debouncing. The switch driver
provides for running a callback or launching a coroutine (coro) on contact
closure and/or opening.

The pushbutton driver extends this to support long-press and double-click
events.

The asynchronous ADC supports pausing a task until the value read from an ADC
goes outside defined bounds.

An IRQ_EVENT class provides a means of interfacing uasyncio to hard or soft
interrupt service routines.

# 1. Contents

 1. [Contents](./DRIVERS.md#1-contents)  
 2. [Installation and usage](./DRIVERS.md#2-installation-and-usage)  
 3. [Interfacing switches](./DRIVERS.md#3-interfacing-switches) Switch debouncer with callbacks.  
  3.1 [Switch class](./DRIVERS.md#31-switch-class)  
 4. [Interfacing pushbuttons](./DRIVERS.md#4-interfacing-pushbuttons) Extends Switch for long and double click events  
  4.1 [Pushbutton class](./DRIVERS.md#41-pushbutton-class)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.1.1 [The suppress constructor argument](./DRIVERS.md#411-the-suppress-constructor-argument)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.1.2 [The sense constructor argument](./DRIVERS.md#412-the-sense-constructor-argument)  
 5. [ADC monitoring](./DRIVERS.md#5-adc-monitoring) Pause until an ADC goes out of bounds  
  5.1 [AADC class](./DRIVERS.md#51-aadc-class)  
  5.2 [Design note](./DRIVERS.md#52-design-note)  
 6. [IRQ_EVENT](./DRIVERS.md#6-irq_event) Interfacing to interrupt service routines.
 7. [Additional functions](./DRIVERS.md#7-additional-functions)  
  7.1 [launch](./DRIVERS.md#71-launch) Run a coro or callback interchangeably  
  7.2 [set_global_exception](./DRIVERS.md#72-set_global_exception) Simplify debugging with a global exception handler  

###### [Tutorial](./TUTORIAL.md#contents)

# 2. Installation and usage

The drivers are in the primitives package. To install copy the `primitives`
directory and its contents to the target hardware.

Drivers are imported with:
```python
from primitives.switch import Switch
from primitives.pushbutton import Pushbutton
from primitives.aadc import AADC
from primitives.irq_event import IRQ_EVENT
```
There is a test/demo program for the Switch and Pushbutton classes. On import
this lists available tests. It assumes a Pyboard with a switch or pushbutton
between X1 and Gnd. It is run as follows:
```python
from primitives.tests.switches import *
test_sw()  # For example
```
The test for the `AADC` class requires a Pyboard with pins X1 and X5 linked. It
is run as follows:
```python
from primitives.tests.adctest import test
test()
```
The test for the `IRQ_EVENT` class requires a Pyboard with pins X1 and X2
linked. It is run as follows:
```python
from primitives.tests.irq_event_test import test
test()
```

###### [Contents](./DRIVERS.md#1-contents)

# 3. Interfacing switches

The `primitives.switch` module provides the `Switch` class. This supports
debouncing a normally open switch connected between a pin and ground. Can run
callbacks or schedule coros on contact closure and/or opening.

In the following text the term `callable` implies a Python `callable`: namely a
function, bound method, coroutine or bound coroutine. The term implies that any
of these may be supplied.

### Timing

The `Switch` class relies on millisecond-level timing: callback functions must
be designed to terminate rapidly. This applies to all functions in the
application; coroutines should yield regularly. If these constraints are not
met, switch events can be missed.

## 3.1 Switch class

This assumes a normally open switch connected between a pin and ground. The pin
should be initialised as an input with a pullup. A `callable` may be specified
to run on contact closure or opening; where the `callable` is a coroutine it
will be converted to a `Task` and will run asynchronously. Debouncing is
implicit: contact bounce will not cause spurious execution of the `callable`.

Constructor argument (mandatory):

 1. `pin` The initialised Pin instance.
 
Methods:

 1. `close_func` Args: `func` (mandatory) a `callable` to run on contact
 closure. `args` a tuple of arguments for the `callable` (default `()`)
 2. `open_func` Args: `func` (mandatory) a `callable` to run on contact open.
 `args` a tuple of arguments for the `callable` (default `()`)
 3. `__call__` Call syntax e.g. `myswitch()` returns the physical debounced
 state of the switch i.e. 0 if grounded, 1 if connected to `3V3`.

Methods 1 and 2 should be called before starting the scheduler.

Class attribute:
 1. `debounce_ms` Debounce time in ms. Default 50.

```python
from pyb import LED
from machine import Pin
import uasyncio as asyncio
from primitives.switch import Switch

async def pulse(led, ms):
    led.on()
    await asyncio.sleep_ms(ms)
    led.off()

async def my_app():
    await asyncio.sleep(60)  # Dummy application code

pin = Pin('X1', Pin.IN, Pin.PULL_UP)  # Hardware: switch to gnd
red = LED(1)
sw = Switch(pin)
sw.close_func(pulse, (red, 1000))  # Note how coro and args are passed
asyncio.run(my_app())  # Run main application code
```

###### [Contents](./DRIVERS.md#1-contents)

# 4. Interfacing pushbuttons

The `primitives.pushbutton` module provides the `Pushbutton` class. This is a
generalisation of `Switch` to support normally open or normally closed switches
connected to ground or 3V3. Can run a `callable` on on press, release,
double-click or long press events.

## 4.1 Pushbutton class

This can support normally open or normally closed switches, connected to `gnd`
(with a pullup) or to `3V3` (with a pull-down). The `Pin` object should be
initialised appropriately. The default state of the switch can be passed in the
optional "sense" parameter on the constructor, otherwise the assumption is that
on instantiation the button is not pressed.

The Pushbutton class uses logical rather than physical state: a button's state
is considered `True` if pressed, otherwise `False` regardless of its physical
implementation.

`callable` instances may be specified to run on button press, release, double
click or long press events; where the `callable` is a coroutine it will be
converted to a `Task` and will run asynchronously.

Please see the note on timing in section 3.

Constructor arguments:

 1. `pin` Mandatory. The initialised Pin instance.
 2. `suppress` Default `False`. See
 [section 4.1.1](./DRIVERS.md#411-the-suppress-constructor-argument).
 3. `sense` Default `None`. Option to define electrical connection. See
 [section 4.1.2](./DRIVERS.md#412-the-sense-constructor-argument).

Methods:

 1. `press_func` Args: `func` (mandatory) a `callable` to run on button push.
 `args` a tuple of arguments for the `callable` (default `()`).
 2. `release_func` Args: `func` (mandatory) a `callable` to run on button
 release. `args` a tuple of arguments for the `callable` (default `()`).
 3. `long_func` Args: `func` (mandatory) a `callable` to run on long button
 push. `args` a tuple of arguments for the `callable` (default `()`).
 4. `double_func` Args: `func` (mandatory) a `callable` to run on double
 push. `args` a tuple of arguments for the `callable` (default `()`).
 5. `__call__` Call syntax e.g. `mybutton()` Returns the logical debounced
 state of the button (`True` corresponds to pressed).
 6. `rawstate()` Returns the logical instantaneous state of the button. There
 is probably no reason to use this.

Methods 1 - 4 should be called before starting the scheduler.

Class attributes:
 1. `debounce_ms` Debounce time in ms. Default 50.
 2. `long_press_ms` Threshold time in ms for a long press. Default 1000.
 3. `double_click_ms` Threshold time in ms for a double click. Default 400.

```python
from pyb import LED
from machine import Pin
import uasyncio as asyncio
from primitives.pushbutton import Pushbutton

def toggle(led):
    led.toggle()

async def my_app():
    await asyncio.sleep(60)  # Dummy

pin = Pin('X1', Pin.IN, Pin.PULL_UP)  # Pushbutton to gnd
red = LED(1)
pb = Pushbutton(pin)
pb.press_func(toggle, (red,))  # Note how function and args are passed
asyncio.run(my_app())  # Run main application code
```

An alternative `Pushbutton` implementation is available
[here](https://github.com/kevinkk525/pysmartnode/blob/dev/pysmartnode/utils/abutton.py):
this implementation avoids the use of the `Delay_ms` class to minimise the
number of coroutines.

### 4.1.1 The suppress constructor argument

When the button is pressed `press_func` runs immediately. This minimal latency
is ideal for applications such as games. Consider a long press: `press_func`
runs initially, then `long_func`, and finally `release_func`. In the case of a
double-click `press_func` and `release_func` will run twice; `double_func` runs
once.

There can be a need for a `callable` which runs if a button is pressed but
only if a doubleclick or long press function does not run. The `suppress` arg
changes the behaviour of `release_func` to fill that role. This has timing
implications.

The soonest that the absence of a long press can be detected is on button
release. Absence of a double click can only be detected when the double click
timer times out without a second press occurring.

Note `suppress` affects the behaviour of `release_func` only. Other callbacks
including `press_func` behave normally.

If the `suppress` constructor arg is set, `release_func` will be launched as
follows:
 1. If `double_func` does not exist on rapid button release.
 2. If `double_func` exists, after the expiration of the doubleclick timer.
 3. If `long_func` exists and the press duration causes `long_func` to be
 launched, `release_func` will not be launched.
 4. If `double_func` exists and a double click occurs, `release_func` will not
 be launched.

In the typical case where `long_func` and `double_func` are both defined, this
ensures that only one of `long_func`, `double_func` and `release_func` run. In
the case of a single short press, `release_func` will be delayed until the
expiry of the double-click timer (because until that time a second click might
occur).

### 4.1.2 The sense constructor argument

In most applications it can be assumed that, at power-up, pushbuttons are not
pressed. The default `None` value uses this assumption to assign the `False`
(not pressed) state at power up. It therefore works with normally open or
normally closed buttons wired to either supply rail. This without programmer
intervention.

In certain use cases this assumption does not hold, and `sense` must explicitly
be specified. This defines the logical state at power-up regardless of whether,
at that time, the button is pressed. Hence `sense=0` defines a button connected
in such a way that when it is not pressed, the voltage on the pin is 0.

When the pin value changes, the new value is compared with `sense` to determine
if the button is closed or open. This is to allow the designer to specify if
the `closed` state of the button is active `high` or active `low`.

###### [Contents](./DRIVERS.md#1-contents)

# 5. ADC monitoring

The `primitives.aadc` module provides the `AADC` (asynchronous ADC) class. This
provides for coroutines which pause until the value returned by an ADC goes
outside predefined bounds. Bounds may be absolute or relative to the current
value. Data from ADC's is usually noisy. Relative bounds provide a simple (if
crude) means of eliminating this. Absolute bounds can be used to raise an alarm
or log data, if the value goes out of range. Typical usage:
```python
import uasyncio as asyncio
from machine import ADC
import pyb
from primitives.aadc import AADC

aadc = AADC(ADC(pyb.Pin.board.X1))
async def foo():
    while True:
        value = await aadc(2000)  # Trigger if value changes by 2000
        print(value)

asyncio.run(foo())
```

## 5.1 AADC class

`AADC` instances are awaitable. This is the principal mode of use.

Constructor argument:
 * `adc` An instance of `machine.ADC`.

Awaiting an instance:  
Function call syntax is used with zero, one or two unsigned integer args. These
determine the bounds for the ADC value.
 * No args: bounds are those set when the instance was last awaited.
 * One integer arg: relative bounds are used. The current ADC value +- the arg.
 * Two args `lower` and `upper`: absolute bounds.

Synchronous methods:
 * `read_u16` arg `last=False` Get the current data from the ADC. If `last` is
 `True` returns the last data read from the ADC. Returns a 16-bit unsigned int
 as per `machine.ADC.read_u16`.
 * `sense(normal)` By default a task awaiting an `AADC` instance will pause
 until the value returned by the ADC exceeds the specified bounds. Issuing
 `sense(False)` inverts this logic: a task will pause until the ADC value is
 within the specified bounds. Issuing `sense(True)` restores normal operation.

In the sample below the coroutine pauses until the ADC is in range, then pauses
until it goes out of range.

```python
import uasyncio as asyncio
from machine import ADC
from primitives.aadc import AADC

aadc = AADC(ADC('X1'))
async def foo():
    while True:
        aadc.sense(normal=False)
        value = await aadc(25_000, 39_000)  # Wait until in range
        print('In range:', value)
        aadc.sense(normal=True)
        value = await aadc()  # Wait until out of range
        print('Out of range:', value)

asyncio.run(foo())
```
## 5.2 Design note

The `AADC` class uses the `uasyncio` stream I/O mechanism. This is not the most
obvious design. It was chosen because the plan for `uasyncio` is that it will
include an option for prioritising I/O. I wanted this class to be able to use
this for applications requiring rapid response.

###### [Contents](./DRIVERS.md#1-contents)

# 6. IRQ_EVENT

Interfacing an interrupt service routine to `uasyncio` requires care. It is
invalid to issue `create_task` or to trigger an `Event` in an ISR as it can
cause a race condition in the scheduler. It is intended that `Event` will
become compatible with soft IRQ's in a future revison of `uasyncio`. See
[iss 6415](https://github.com/micropython/micropython/issues/6415),
[PR 6106](https://github.com/micropython/micropython/pull/6106) and
[iss 5795](https://github.com/micropython/micropython/issues/5795).

Currently there are two ways of interfacing hard or soft IRQ's with `uasyncio`.
One is to use a busy-wait loop as per the
[Message](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#36-message)
primitive. A more efficient approach is to use this `IRQ_EVENT` class. The API
is a subset of the  `Event` class, so if official `Event` becomes thread-safe
it may readily be substituted. The `IRQ_EVENT` class uses uses the `uasyncio`
I/O mechanism to achieve thread-safe operation.

Unlike `Event` only one task can wait on an `IRQ_EVENT`.

Constructor:
 * This has no args.

Synchronous Methods:
 * `set()` Initiates the event. May be called from a hard or soft ISR. Returns
 fast.
 * `is_set()` Returns `True` if the irq_event is set.
 * `clear()` This does nothing; its purpose is to enable code to be written
 compatible with a future thread-safe `Event` class, with the ISR setting then
 immediately clearing the event.

Asynchronous Method:
 * `wait` Pause until irq_event is set. The irq_event is cleared.

A single task waits on the event by issuing `await irq_event.wait()`; execution
pauses until the ISR issues `irq_event.set()`. Execution of the paused task
resumes when it is next scheduled. Under current `uasyncio` (V3.0.0) scheduling
of the paused task does not occur any faster than using busy-wait. In typical
use the ISR services the interrupting device, saving received data, then sets
the irq_event to trigger processing of the received data.

If interrupts occur faster than `uasyncio` can schedule the paused task, more
than one interrupt may occur before the paused task runs.

Example usage (assumes a Pyboard with pins X1 and X2 linked):
```python
from machine import Pin
from pyb import LED
import uasyncio as asyncio
import micropython
from primitives.irq_event import IRQ_EVENT

micropython.alloc_emergency_exception_buf(100)

driver = Pin(Pin.board.X2, Pin.OUT)
receiver = Pin(Pin.board.X1, Pin.IN)
evt_rx = IRQ_EVENT()  # IRQ_EVENT instance for receiving Pin

def pin_han(pin):  # Hard IRQ handler. Typically services a device
    evt_rx.set()  # then issues this which returns quickly

receiver.irq(pin_han, Pin.IRQ_FALLING, hard=True)  # Set up hard ISR

async def pulse_gen(pin):
    while True:
        await asyncio.sleep_ms(500)
        pin(not pin())

async def red_handler(evt_rx, iterations):
    led = LED(1)
    for x in range(iterations):
        await evt_rx.wait()  # Pause until next interrupt
        print(x)
        led.toggle()

async def irq_test(iterations):
    pg = asyncio.create_task(pulse_gen(driver))
    await red_handler(evt_rx, iterations)
    pg.cancel()

def test(iterations=20):
    try:
        asyncio.run(irq_test(iterations))
    finally:
        asyncio.new_event_loop()
```

###### [Contents](./DRIVERS.md#1-contents)

# 7. Additional functions

## 7.1 Launch

Importe as follows:
```python
from primitives import launch
```
`launch` enables a function to accept a coro or a callback interchangeably. It
accepts the callable plus a tuple of args. If a callback is passed, `launch`
runs it and returns the callback's return value. If a coro is passed, it is
converted to a `task` and run asynchronously. The return value is the `task`
instance. A usage example is in `primitives/switch.py`.

## 7.2 set_global_exception

Import as follows:
```python
from primitives import set_global_exception
```
`set_global_exception` is a convenience funtion to enable a global exception
handler to simplify debugging. The function takes no args. It is called as
follows:

```python
import uasyncio as asyncio
from primitives import set_global_exception

async def main():
    set_global_exception()
    # Main body of application code omitted

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()  # Clear retained state
```
This is explained in the tutorial. In essence if an exception occurs in a task,
the default behaviour is for the task to stop but for the rest of the code to
continue to run. This means that the failure can be missed and the sequence of
events can be hard to deduce. A global handler ensures that the entire
application stops allowing the traceback and other debug prints to be studied.

###### [Contents](./DRIVERS.md#1-contents)
