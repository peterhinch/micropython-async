# 1. Introduction

Drivers for switches and pushbuttons are provided, plus a retriggerable delay
class. The switch and button drivers support debouncing. The switch driver
provides for running a callback or launching a coroutine (coro) on contact
closure and/or opening.

The pushbutton driver extends this to support long-press and double-click
events.

# 2. Modules

 1. `aledflash.py` Flashes the four Pyboard LED's asynchronously for 10s. The
 simplest uasyncio demo. Import it to run.
 2. `aswitch.py` This provides classes for interfacing switches and pushbuttons
 and also a software retriggerable delay object. Pushbuttons are a
 generalisation of switches providing logical rather than physical status along
 with double-clicked and long pressed events.
 3. `astests.py` Test/demonstration programs for `aswitch.py`.

# 3. Module aswitch.py

This module provides the following classes:

 * `Switch` This supports debouncing a normally open switch connected between
 a pin and ground. Can run callbacks or schedule coros on contact closure
 and/or opening.
 * `Pushbutton` A generalisation of `Switch` to support normally open or
 normally closed switches connected to ground or 3V3. Can run callbacks or
 schedule coros on double-click or long press events.
 * `Delay_ms` A class providing a retriggerable delay measured in ms. Can be
 used to run a callback or to schedule a coro. Its state can be tested by any
 coro.
 
The module `astests.py` provides examples of usage. In the following text the
term **function** implies a Python `callable`: namely a function, bound method,
coroutine or bound coroutine interchangeably.

### Timing

The `Switch` class relies on millisecond-level timing: callback functions must
be designed to terminate rapidly. This applies to all functions in the
application; coroutines should yield regularly. If these constraints are not
met, switch events can be missed.

## 3.1 Switch class

This assumes a normally open switch connected between a pin and ground. The pin
should be initialised as an input with a pullup. A **function** may be
specified to run on contact closure or opening; where the **function** is a
coroutine it will be scheduled for execution and will run asynchronously.
Debouncing is implicit: contact bounce will not cause spurious execution of
these functions.

Constructor argument (mandatory):

 1. `pin` The initialised Pin instance.
 
Methods:

 1. `close_func` Args: `func` (mandatory) a **function** to run on contact
 closure. `args` a tuple of arguments for the **function** (default `()`)
 2. `open_func` Args: `func` (mandatory) a **function** to run on contact open.
 `args` a tuple of arguments for the **function** (default `()`)
 3. `__call__` Call syntax e.g. `myswitch()` returns the physical debounced
 state of the switch i.e. 0 if grounded, 1 if connected to `3V3`.

Methods 1 and 2 should be called before starting the scheduler.

Class attribute:
 1. `debounce_ms` Debounce time in ms. Default 50.

```python
from pyb import LED
from machine import Pin
import uasyncio as asyncio
from aswitch import Switch

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
loop = asyncio.get_event_loop()
loop.run_until_complete(my_app())  # Run main application code
```

## 3.2 Pushbutton class

This can support normally open or normally closed switches, connected to `gnd`
(with a pullup) or to `3V3` (with a pull-down). The `Pin` object should be
initialised appropriately. The assumption is that on initialisation the button
is not pressed.

The Pushbutton class uses logical rather than physical state: a button's state
is considered `True` if pressed, otherwise `False` regardless of its physical
implementation.

**function** instances may be specified to run on button press, release, double
click or long press events; where the **function** is a coroutine it will be
scheduled for execution and will run asynchronously.

Please see the note on timing in section 3.

Constructor arguments:

 1. `pin` Mandatory. The initialised Pin instance.
 2. `suppress` Default `False`. See 3.2.1 below.

Methods:

 1. `press_func` Args: `func` (mandatory) a **function** to run on button push.
 `args` a tuple of arguments for the **function** (default `()`).
 2. `release_func` Args: `func` (mandatory) a **function** to run on button
 release. `args` a tuple of arguments for the **function** (default `()`).
 3. `long_func` Args: `func` (mandatory) a **function** to run on long button
 push. `args` a tuple of arguments for the **function** (default `()`).
 4. `double_func` Args: `func` (mandatory) a **function** to run on double
 push. `args` a tuple of arguments for the **function** (default `()`).
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
from aswitch import Pushbutton

def toggle(led):
    led.toggle()

async def my_app():
    await asyncio.sleep(60)  # Dummy

pin = Pin('X1', Pin.IN, Pin.PULL_UP)  # Pushbutton to gnd
red = LED(1)
pb = Pushbutton(pin)
pb.press_func(toggle, (red,))  # Note how function and args are passed
loop = asyncio.get_event_loop()
loop.run_until_complete(my_app())  # Run main application code
```

An alternative Pushbutton class with lower RAM usage is available
[here](https://github.com/kevinkk525/pysmartnode/blob/dev/pysmartnode/utils/abutton.py).

### 3.2.1 The suppress constructor argument

When the button is pressed `press_func` runs immediately. This minimal latency
is ideal for applications such as games, but does imply that in the event of a
long press, both `press_func` and `long_func` run: `press_func` immediately and
`long_func` if the button is still pressed when the timer has elapsed. Similar
reasoning applies to the double click function.

There can be a need for a **function** which runs if a button is pressed but
only if a doubleclick or long press function does not run. The soonest that the
absence of a long press can be detected is on button release. The absence of a
double click can only be detected when the double click timer times out without
a second press occurring.

This **function** is the `release_func`. If the `suppress` constructor arg is
set, `release_func` will be launched as follows:
 1. If `double_func` does not exist on rapid button release.
 2. If `double_func` exists, after the expiration of the doubleclick timer.
 3. If `long_func` exists and the press duration causes `long_func` to be
 launched, `release_func` will not be launched.
 4. If `double_func` exists and a double click occurs, `release_func` will not
 be launched.

## 3.3 Delay_ms class

This implements the software equivalent of a retriggerable monostable or a
watchdog timer. It has an internal boolean `running` state. When instantiated
the `Delay_ms` instance does nothing, with `running` `False` until triggered.
Then `running` becomes `True` and a timer is initiated. This can be prevented
from timing out by triggering it again (with a new timeout duration). So long
as it is triggered before the time specified in the preceeding trigger it will
never time out.

If it does time out the `running` state will revert to `False`. This can be
interrogated by the object's `running()` method. In addition a **function** can
be specified to the constructor. This will execute when a timeout occurs; where
the **function** is a coroutine it will be scheduled for execution and will run
asynchronously.

Constructor arguments (defaults in brackets):

 1. `func` The **function** to call on timeout (default `None`).
 2. `args` A tuple of arguments for the **function** (default `()`).
 3. `can_alloc` Boolean, default `True`. See below.
 4. `duration` Integer, default 1000ms. The default timer period where no value
 is passed to the `trigger` method.

Methods:

 1. `trigger` optional argument `duration=0`. A timeout will occur after
 `duration` ms unless retriggered. If no arg is passed the period will be that
 of the `duration` passed to the constructor. See Class variable below.
 2. `stop` No argument. Cancels the timeout, setting the `running` status
 `False`. The timer can be restarted by issuing `trigger` again.
 3. `running` No argument. Returns the running status of the object.
 4. `__call__` Alias for running.

Class variable:

 1. `verbose=False` If `True` a warning will be printed if a running timer is
 retriggered with a time value shorter than the time currently outstanding.
 Such an operation has no effect owing to the design of `uasyncio`.

If the `trigger` method is to be called from an interrupt service routine the
`can_alloc` constructor arg should be `False`. This causes the delay object
to use a slightly less efficient mode which avoids RAM allocation when
`trigger` runs.

In this example a 3 second timer starts when the button is pressed. If it is
pressed repeatedly the timeout will not be triggered. If it is not pressed for
3 seconds the timeout triggers and the LED lights.

```python
from pyb import LED
from machine import Pin
import uasyncio as asyncio
from aswitch import Pushbutton, Delay_ms

async def my_app():
    await asyncio.sleep(60)  # Run for 1 minute

pin = Pin('X1', Pin.IN, Pin.PULL_UP)  # Pushbutton to gnd
red = LED(1)
pb = Pushbutton(pin)
d = Delay_ms(lambda led: led.on(), (red,))
pb.press_func(d.trigger, (3000,))  # Note how function and args are passed
loop = asyncio.get_event_loop()
loop.run_until_complete(my_app())  # Run main application code
```

# 4. Module astests.py

This provides demonstration/test functions for the `Switch` and `Pushbutton`
classes. They assume a switch or button wired between pin X1 and gnd. Tests may
be terminated by grounding X2.

## 4.1 Function test_sw()

This will flash the red LED on switch closure, and the green LED on opening
and demonstrates the scheduling of coroutines. See section 5 for a discussion
of its behaviour if the switch is toggled rapidly.

## 4.2 Function test_swcb()

Demonstrates the use of callbacks to toggle the red and green LED's.

## 4.3 Function test_btn(lpmode=False)

This will flash the red LED on button push, and the green LED on release. A
long press will flash the blue LED and a double-press the yellow one.

Test the launching of coroutines and also the `suppress` constructor arg.

It takes three optional positional boolean args:
 1. `Suppresss=False` If `True` sets the `suppress` constructor arg.
 2. `lf=True` Declare a long press coro.
 3. `df=true` Declare a double click coro.

The note below on race conditions applies.

## 4.4 Function test_btncb()

Demonstrates the use of callbacks. Toggles the red, green, yellow and blue
LED's on press, release, double-press and long press respectively.

# 5 Race conditions

Note that in the tests such as test_sw() where coroutines are scheduled by
events and the switch is cycled rapidly the LED behaviour may seem surprising.
This is because each time the switch is closed a coro is launched to flash the
red LED; on each open event one is launched for the green LED. With rapid
cycling a new coro instance will commence while one is still running against
the same LED. This type of conflict over a resource is known as a race
condition: in this instance it leads to the LED behaving erratically.

This is a hazard of asynchronous programming. In some situations it is
desirable to launch a new instance on each button press or switch closure, even
if other instances are still incomplete. In other cases it can lead to a race
condition, leading to the need to code an interlock to ensure that the desired
behaviour occurs. The programmer must define the desired behaviour.

In the case of this test program it might be to ignore events while a similar
one is running, or to extend the timer to prolong the LED illumination.
Alternatively a subsequent button press might be required to terminate the
illumination. The "right" behaviour is application dependent.

A further consequence of scheduling new coroutine instances when one or more
are already running is that the `uasyncio` queue can fill causing an exception.
