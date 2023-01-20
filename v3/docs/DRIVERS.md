# 0. Introduction

Drivers for switches and pushbuttons are provided. Switch and button drivers
support debouncing. The switch driver provides for running a callback or
launching a coroutine (coro) on contact closure and/or opening. The pushbutton
driver extends this to support long-press and double-click events. The drivers
now support an optional event driven interface as a more flexible alternative
to callbacks.

An `Encoder` class is provided to support rotary control knobs based on
quadrature encoder switches. This is not intended for high throughput encoders
as used in CNC machines where
[an interrupt based solution](https://github.com/peterhinch/micropython-samples#47-rotary-incremental-encoder)
is required.

The asynchronous ADC supports pausing a task until the value read from an ADC
goes outside defined bounds.

# 1. Contents

 1. [Contents](./DRIVERS.md#1-contents)  
 2. [Installation and usage](./DRIVERS.md#2-installation-and-usage)  
 3. [Interfacing switches](./DRIVERS.md#3-interfacing-switches) Switch debouncer with callbacks.  
  3.1 [Switch class](./DRIVERS.md#31-switch-class)  
  3.2 [Event interface](./DRIVERS.md#32-event-interface)  
 4. [Interfacing pushbuttons](./DRIVERS.md#4-interfacing-pushbuttons) Extends Switch for long and double-click events  
  4.1 [Pushbutton class](./DRIVERS.md#41-pushbutton-class)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.1.1 [The suppress constructor argument](./DRIVERS.md#411-the-suppress-constructor-argument)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.1.2 [The sense constructor argument](./DRIVERS.md#412-the-sense-constructor-argument)  
  4.2 [ESP32Touch class](./DRIVERS.md#42-esp32touch-class)  
 5. [ADC monitoring](./DRIVERS.md#5-adc-monitoring) Pause until an ADC goes out of bounds  
  5.1 [AADC class](./DRIVERS.md#51-aadc-class)  
  5.2 [Design note](./DRIVERS.md#52-design-note)  
 6. [Quadrature encoders](./DRIVERS.md#6-quadrature-encoders)  
  6.1 [Encoder class](./DRIVERS.md#61-encoder-class)  
 7. [Additional functions](./DRIVERS.md#7-additional-functions)  
  7.1 [launch](./DRIVERS.md#71-launch) Run a coro or callback interchangeably  
  7.2 [set_global_exception](./DRIVERS.md#72-set_global_exception) Simplify debugging with a global exception handler.  
 8. [Event based interface](./DRIVERS.md#8-event-based-interface) An alternative interface to Switch and Pushbutton objects.  

###### [Tutorial](./TUTORIAL.md#contents)

# 2. Installation and usage

The drivers require firmware version >=1.15. The drivers are in the primitives
package. To install copy the `primitives` directory and its contents to the
target hardware.

Drivers are imported with:
```python
from primitives import Switch, Pushbutton, AADC
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

###### [Contents](./DRIVERS.md#1-contents)

# 3. Interfacing switches

The `primitives.switch` module provides the `Switch` class. This supports
debouncing a normally open switch connected between a pin and ground. Can run
callbacks or schedule coros on contact closure and/or opening. As an
alternative to a callback based interface, bound `Event` objects may be
triggered on switch state changes. To use an `Event` based interface
exclusively see the simpler [ESwitch class](./EVENTS.md#61-eswitch).

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
 4. `deinit` No args. Cancels the running task.

Class attribute:
 1. `debounce_ms` Debounce time in ms. Default 50.

```python
from pyb import LED
from machine import Pin
import uasyncio as asyncio
from primitives import Switch

async def pulse(led, ms):
    led.on()
    await asyncio.sleep_ms(ms)
    led.off()

async def my_app():
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)  # Hardware: switch to gnd
    red = LED(1)
    sw = Switch(pin)
    sw.close_func(pulse, (red, 1000))  # Note how coro and args are passed
    await asyncio.sleep(60)  # Dummy application code

asyncio.run(my_app())  # Run main application code
```

## 3.2 Event interface

This enables a task to wait on a switch state as represented by a bound `Event`
instance. A bound contact closure `Event` is created by passing `None` to
`.close_func`, in which case the `Event` is named `.close`. Likewise a `.open`
`Event` is created by passing `None` to `open_func`.

This is discussed further in
[Event based interface](./DRIVERS.md#8-event-based-interface) which includes a
code example. This API and the simpler [ESwitch class](./EVENTS.md#61-eswitch)
is recommended for new projects.

###### [Contents](./DRIVERS.md#1-contents)

# 4. Interfacing pushbuttons

The `primitives.pushbutton` module provides the `Pushbutton` class for use with
simple mechanical, spring-loaded push buttons. This class is a generalisation
of the `Switch` class. `Pushbutton` supports open or normally closed buttons
connected to ground or 3V3. To a human, pushing a button is seen as a single
event, but the micro-controller sees voltage changes corresponding to two
events: press and release. A long button press adds the component of time and a
double-click appears as four voltage changes. The asynchronous `Pushbutton`
class provides the logic required to handle these user interactions by
monitoring these events over time.

Instances of this class can run a `callable` on press, release, double-click or
long press events.

As an alternative to callbacks bound `Event` instances may be created which are
triggered by press, release, double-click or long press events. This mode of
operation is more flexible than the use of callbacks and is covered in
[Event based interface](./DRIVERS.md#8-event-based-interface). To use an
`Event` based interface exclusively see the simpler
[EButton class](./EVENTS.md#62-ebutton).

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

Please see the note on timing in [section 3](./DRIVERS.md#3-interfacing-switches).

Constructor arguments:

 1. `pin` Mandatory. The initialised Pin instance.
 2. `suppress` Default `False`. See
 [section 4.1.1](./DRIVERS.md#411-the-suppress-constructor-argument).
 3. `sense` Default `None`. Option to define electrical connection. See
 [section 4.1.2](./DRIVERS.md#412-the-sense-constructor-argument).

Methods:

 1. `press_func` Args: `func=False` a `callable` to run on button push,
 `args=()` a tuple of arguments for the `callable`.
 2. `release_func` Args: `func=False` a `callable` to run on button release,
 `args=()` a tuple of arguments for the `callable`.
 3. `long_func` Args: `func=False` a `callable` to run on long button push,
 `args=()` a tuple of arguments for the `callable`.
 4. `double_func` Args: `func=False` a `callable` to run on double push,
 `args=()` a tuple of arguments for the `callable`.
 5. `__call__` Call syntax e.g. `mybutton()` Returns the logical debounced
 state of the button (`True` corresponds to pressed).
 6. `rawstate()` Returns the logical instantaneous state of the button. There
 is probably no reason to use this.
 7. `deinit` No args. Cancels the running task.

Methods 1 - 4 may be called at any time. If `False` is passed for a callable,
any existing callback will be disabled. If `None` is passed, a bound `Event` is
created. See [Event based interface](./DRIVERS.md#8-event-based-interface).

Class attributes:
 1. `debounce_ms` Debounce time in ms. Default 50.
 2. `long_press_ms` Threshold time in ms for a long press. Default 1000.
 3. `double_click_ms` Threshold time in ms for a double-click. Default 400.

A simple Pyboard demo:
```python
from pyb import LED
from machine import Pin
import uasyncio as asyncio
from primitives import Pushbutton

def toggle(led):
    led.toggle()

async def my_app():
    pin = Pin('X1', Pin.IN, Pin.PULL_UP)  # Pushbutton to gnd
    red = LED(1)
    pb = Pushbutton(pin)
    pb.press_func(toggle, (red,))  # Note how function and args are passed
    await asyncio.sleep(60)  # Dummy

asyncio.run(my_app())  # Run main application code
```

A `Pushbutton` subset is available
[here](https://github.com/kevinkk525/pysmartnode/blob/dev/pysmartnode/utils/abutton.py):
this implementation avoids the use of the `Delay_ms` class to minimise the
number of coroutines.

### 4.1.1 The suppress constructor argument

The purpose of the `suppress` argument is to disambiguate the response when an
application requires either, or both, long-press and double-click events. It
works by modifying the behavior of the `release_func`. By design, whenever a
button is pressed, the `press_func` runs immediately. This minimal latency is
ideal for applications such as games. The `Pushbutton` class provides the
ability to suppress 'intermediate' events and reduce them down to one single
event. The `suppress` argument is useful for applications where long-press,
single-press, and double-click events are desired, such as clocks, watches, or
menu navigation. However, long-press and double-click detection introduces
additional latency to ensure correct classification of events and is therefore
not suitable for all applications. To illustrate the default library behavior,
consider how long button presses and double-clicks are interpreted.

A long press is seen as three events:

 * `press_func`
 * `long_func`
 * `release_func`

Similarly, a double-click is seen as five events:

 * `press_func`
 * `release_func`
 * `press_func`
 * `release_func`
 * `double_func`

There can be a need for a callable which runs if a button is pressed, but only
if a double-click or long-press function does not run. The suppress argument
changes the behaviour of the `release_func` to fill that role. This has timing
implications. The soonest that the absence of a long press can be detected is
on button release. Absence of a double-click can only be detected when the
double-click timer times out without a second press occurring.

Note: `suppress` affects the behaviour of the `release_func` only. Other
callbacks including `press_func` behave normally.

If the `suppress = True` constructor argument is set, the `release_func` will
be launched as follows:

 * If `double_func` does not exist on rapid button release.
 * If `double_func` exists, after the expiration of the double-click timer.
 * If `long_func` exists and the press duration causes `long_func` to be
 launched, `release_func` will not be launched.
 * If `double_func` exists and a double-click occurs, `release_func` will not
 be launched.

In the typical case where `long_func` and `double_func` are both defined, this
ensures that only one of `long_func`, `double_func` and `release_func` run. In
the case of a single short press, the `release_func` will be delayed until the
expiry of the double-click timer (because until that time a second click might
occur).

The following script may be used to demonstrate the effect of this argument. As
written, it assumes a Pi Pico with a push button attached between GPIO 18 and
Gnd, with the primitives installed.
```python
from machine import Pin
import uasyncio as asyncio
from primitives import Pushbutton

btn = Pin(18, Pin.IN, Pin.PULL_UP)  # Adapt for your hardware
pb = Pushbutton(btn, suppress=True)

async def main():
    short_press = pb.release_func(print, ("SHORT",))
    double_press = pb.double_func(print, ("DOUBLE",))
    long_press = pb.long_func(print, ("LONG",))
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
```

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

## 4.2 ESP32Touch class

This subclass of `Pushbutton` supports ESP32 touchpads providing a callback
based interface. See the
[official docs](http://docs.micropython.org/en/latest/esp32/quickref.html#capacitive-touch).

API and usage are as per `Pushbutton` with the following provisos:
 1. The `sense` constructor arg is not supported.
 2. The `Pin` instance passed to the constructor must support the touch
 interface. It is instantiated without args, as per the example below.
 3. There is an additional classmethod `threshold` which takes an integer arg.
 The arg represents the detection threshold as a percentage.

The driver determines the untouched state by periodically polling
`machine.TouchPad.read()` and storing its maximum value. If it reads a value
below `maximum * threshold / 100` a touch is deemed to have occurred. Default
threshold is currently 80% but this is subject to change.

Example usage:
```python
from machine import Pin
import uasyncio as asyncio
from primitives import ESP32Touch

ESP32Touch.threshold(70)  # optional

async def main():
    tb = ESP32Touch(Pin(15), suppress=True)
    tb.press_func(lambda : print("press"))
    tb.double_func(lambda : print("double"))
    tb.long_func(lambda : print("long"))
    tb.release_func(lambda : print("release"))
    while True:
        await asyncio.sleep(1)

asyncio.run(main())
```
If a touchpad is touched on initialisation no callbacks will occur even when
the pad is released. Initial button state is always `False`. Normal behaviour
will commence with subsequent touches.

The best threshold value depends on physical design. Directly touching a large
pad will result in a low value from `machine.TouchPad.read()`. A small pad
covered with an insulating film will yield a smaller change.

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
from primitives import AADC

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
from primitives import AADC

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

# 6. Quadrature encoders

The [Encoder](https://github.com/peterhinch/micropython-async/blob/master/v3/primitives/encoder.py)
class is an asynchronous driver for control knobs based on quadrature encoder
switches such as
[this Adafruit product](https://www.adafruit.com/product/377). The driver is
not intended for applications such as CNC machines where
[a solution such as this one](https://github.com/peterhinch/micropython-samples#47-rotary-incremental-encoder)
is required. Drivers for NC machines must never miss an edge. Contact bounce or
vibration induced jitter can cause transitions to occur at a high rate; these
must be tracked. Consequently callbacks occur in an interrupt context with the
associated concurrency issues. These issues, along with general discussion of
MicroPython encoder drivers, are covered
[in this doc](https://github.com/peterhinch/micropython-samples/blob/master/encoders/ENCODERS.md).

This driver runs the user supplied callback in an `asyncio` context, so that
the callback runs only when other tasks have yielded to the scheduler. This
ensures that the callback runs with the same rules as apply to any `uasyncio`
task. This offers safety, even if the task triggers complex application
behaviour.

The `Encoder` can be instantiated in such a way that its effective resolution
can be reduced. A virtual encoder with lower resolution can be useful in some
applications.

The driver allows limits to be assigned to the virtual encoder's value so that
a dial running from (say) 0 to 100 may be implemented. If limits are used,
encoder values no longer approximate absolute angles: the user might continue
to rotate the dial when its value is "stuck" at an endstop.

The callback only runs if a change in position of the virtual encoder has
occurred. In consequence of the callback running in an `asyncio` context, by
the time it is scheduled, the encoder's position may have changed by more than
one increment. The callback receives two args, the absolute value of the
virtual encoder at the time it was triggered and the signed change in this
value since the previous time the callback ran.

## 6.1 Encoder class

Existing users: the `delay` parameter is now a constructor arg rather than a
class varaiable.

Constructor arguments:  
 1. `pin_x` Initialised `machine.Pin` instances for the switch. Should be set
 as `Pin.IN` and have pullups.
 2. `pin_y` Ditto.
 3. `v=0` Initial value.
 4. `div=1` A value > 1 causes the motion rate of the encoder to be divided
 down, to produce a virtual encoder with lower resolution. This can enable
 tracking of mechanical detents - typical values are then 4 or 2 pulses per
 click.
 5. `vmin=None` By default the `value` of the encoder can vary without limit.
 Optionally maximum and/or minimum limits can be set.
 6. `vmax=None` As above. If `vmin` and/or `vmax` are specified, a `ValueError`
 will be thrown if the initial value `v` does not conform with the limits.
 7. `mod=None` An integer `N > 0` causes the divided value to be reduced modulo
 `N` - useful for controlling rotary devices.
 8. `callback=lambda a, b : None` Optional callback function. The callback
 receives two integer args, `v` being the virtual encoder's current value and
 `delta` being the signed difference between the current value and the previous
 one. Further args may be appended by the following.
 9. `args=()` An optional tuple of positionl args for the callback.
 10. `delay=100` After motion is detected the driver waits for `delay` ms before
 reading the current position. A delay can be used to limit the rate at which
 the callback is invoked. This is a minimal approach. See
 [this script](https://github.com/peterhinch/micropython-async/blob/master/v3/primitives/tests/encoder_stop.py)
 for a way to create a callback which runs only when the encoder stops moving.

 Synchronous method:  
 * `value` No args. Returns an integer being the virtual encoder's current
 value.

Not all combinations of arguments make mathematical sense. The order in which
operations are applied is:
 1. Apply division if specified.
 2. Restrict the divided value by any maximum or minimum.
 3. Reduce modulo N if specified.

See [this doc](https://github.com/peterhinch/micropython-samples/blob/master/encoders/ENCODERS.md)
for further information on encoders and their limitations.

###### [Contents](./DRIVERS.md#1-contents)

# 7. Additional functions

## 7.1 Launch

Import as follows:
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

# 8. Event based interface

The `Switch` and `Pushbutton` classes offer a traditional callback-based
interface. While familiar, it has drawbacks and requires extra code to perform
tasks like retrieving the result of a callback or, where a task is launched,
cancelling that task. The reason for this API is historical; an efficient
`Event` class only materialised with `uasyncio` V3. The class ensures that a
task waiting on an `Event` consumes minimal processor time.

It is suggested that this API is used in new projects.

The event based interface to `Switch` and `Pushbutton` classes is engaged by
passing `None` to the methods used to register callbacks. This causes a bound
`Event` to be instantiated, which may be accessed by user code.

The following shows the name of the bound `Event` created when `None` is passed
to a method:

| Class      | method       | Event   |
|:-----------|:-------------|:--------|
| Switch     | close_func   | close   |
| Switch     | open_func    | open    |
| Pushbutton | press_func   | press   |
| Pushbutton | release_func | release |
| Pushbutton | long_func    | long    |
| Pushbutton | double_func  | double  |

Typical usage is as follows:
```python
import uasyncio as asyncio
from primitives import Switch
from pyb import Pin

async def foo(evt):
    while True:
        evt.clear()  # re-enable the event
        await evt.wait()  # minimal resources used while paused
        print("Switch closed.")
        # Omitted code runs each time the switch closes

async def main():
    sw = Switch(Pin("X1", Pin.IN, Pin.PULL_UP))
    sw.close_func(None)  # Use event based interface
    await foo(sw.close)  # Pass the bound event to foo

asyncio.run(main())
```
With appropriate code the behaviour of the callback based interface may be
replicated, but with added benefits. For example the omitted code in `foo`
could run a callback-style synchronous method, retrieving its value.
Alternatively the code could create a task which could be cancelled.

###### [Contents](./DRIVERS.md#1-contents)
