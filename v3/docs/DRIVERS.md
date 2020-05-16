# 1. Introduction

Drivers for switches and pushbuttons are provided, plus a retriggerable delay
class. The switch and button drivers support debouncing. The switch driver
provides for running a callback or launching a coroutine (coro) on contact
closure and/or opening.

The pushbutton driver extends this to support long-press and double-click
events.

The asynchronous ADC supports pausing a task until the value read from an ADC
goes outside defined bounds.

###### [Tutorial](./TUTORIAL.md#contents)

# 2. Installation and usage

The drivers are in the primitives package. To install copy the `primitives`
directory and its contents to the target hardware.

Drivers are imported with:
```python
from primitives.switch import Switch
from primitives.pushbutton import Pushbutton
from primitives.aadc import AADC
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

# 3. primitives.switch

This module provides the `Switch` class. This supports debouncing a normally
open switch connected between a pin and ground. Can run callbacks or schedule
coros on contact closure and/or opening.

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

# 4. primitives.pushbutton

The `Pushbutton` class is generalisation of `Switch` to support normally open
or normally closed switches connected to ground or 3V3. Can run a `callable` on
on press, release, double-click or long press events.

## 4.1 Pushbutton class

This can support normally open or normally closed switches, connected to `gnd`
(with a pullup) or to `3V3` (with a pull-down). The `Pin` object should be
initialised appropriately. The assumption is that on instantiation the button
is not pressed.

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
 [4.2.1](./DRIVERS.md#421-the-suppress-constructor-argument).

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

An alternative Pushbutton class with lower RAM usage is available
[here](https://github.com/kevinkk525/pysmartnode/blob/dev/pysmartnode/utils/abutton.py).

### 4.1.1 The suppress constructor argument

When the button is pressed `press_func` runs immediately. This minimal latency
is ideal for applications such as games, but does imply that in the event of a
long press, both `press_func` and `long_func` run: `press_func` immediately and
`long_func` if the button is still pressed when the timer has elapsed. Similar
reasoning applies to the double click function.

There can be a need for a `callable` which runs if a button is pressed but
only if a doubleclick or long press function does not run. The soonest that the
absence of a long press can be detected is on button release. The absence of a
double click can only be detected when the double click timer times out without
a second press occurring.

This `callable` is the `release_func`. If the `suppress` constructor arg is
set, `release_func` will be launched as follows:
 1. If `double_func` does not exist on rapid button release.
 2. If `double_func` exists, after the expiration of the doubleclick timer.
 3. If `long_func` exists and the press duration causes `long_func` to be
 launched, `release_func` will not be launched.
 4. If `double_func` exists and a double click occurs, `release_func` will not
 be launched.


# 5. primitives.aadc

The `AADC` (asynchronous ADC) class provides for coroutines which pause until
the value returned by an ADC goes outside predefined bounds. The bounds can be
absolute or relative to the current value. The data from ADC's is usually
noisy. Relative bounds provide a simple (if crude) means of eliminating this.
Absolute bounds can be used to raise an alarm, or log data, if the value goes
out of range. Typical usage:
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
