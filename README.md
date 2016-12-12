# Some uasyncio hardware drivers

This document describes some device drivers and example programs using uasyncio
to access hardware devices.

A more general tutorial on using uasyncio is [here](./TUTORIAL.md) - warning
this is a work-in-progress and may contain errors.

In general cooperative muti tasking simplifies the design of many types of
embedded applications without incurring the overheads and many of the hazards
of pre-emptive paradigms. It is particularly well suited to applications
involving user interfaces. The official way to achieve it in MicroPython is
to use the uasyncio library.

# 1. Installation of uasyncio

Firstly install the latest version of ``micropython-uasyncio``. To use queues, also
install the ``micropython-uasyncio.queues`` module.

Instructions on installing library modules may be found [here](https://github.com/micropython/micropython-lib).

On networked hardware, upip may be run locally.

On non-networked hardware the resultant modules will need to be copied to the
target. The above Unix installation will create directories under
``~/.micropython/lib`` which may be copied to the target hardware, either to
the root or to a ``lib`` subdirectory. Alternatively the device may be mounted;
then use the "-p" option to upip to specify the target directory as the mounted
filesystem.

# 2. Modules

 1. ``aledflash.py`` Flashes the four Pyboard LED's asynchronously for 10s. The
 simplest uasyncio demo. Import it to run.
 2. ``aswitch.py`` This provides classes for interfacing switches and
 pushbuttons and also a software retriggerable delay object. Pushbuttons are a
 generalisation of switches providing logical rather than physical status along
 with double-clicked and long pressed events.
 3. ``astests.py`` Test/demonstration programs for the above.

# 3. Module aswitch.py

This module provides the following classes:

 * ``Switch`` This supports debouncing a normally open switch connected between a
 pin and ground. Can schedule coros on contact closure and/or opening.
 * ``Pushbutton`` A generalisation of ``Switch`` to support normally open or
 normally closed switches connected to ground or 3V3. Can also schedule
 coros on double-click or long press events.
 * ``Delay_ms`` A class providing a retriggerable delay measured in ms. Can be
 used to schedule a coro. Alternatively its state can be tested by any coro.
 
The module ``astests.py`` provides examples of usage.

## 3.1 Switch class

This assumes a normally open switch connected between a pin and ground. The pin
should be initialised as an input with a pullup.

Constructor argument (mandatory):

 1. ``pin`` The initialised Pin instance.
 
Methods:

 1. ``close_coro`` Args: ``coro`` (mandatory) a coro to run on contact closure.
 ``args`` a tuple of arguments for the coro (default ())
 2. ``open_coro`` Args: ``coro`` (mandatory) a coro to run on contact open.
 ``args`` a tuple of arguments for the coro (default ())
 3. ``__call__`` Call syntax e.g. ``myswitch()`` returns the physical debounced
 state of the switch i.e. 0 if grounded, 1 if connected to ``3V3``.

Class attribute:
 1. ``debounce_ms`` Debounce time in ms. Default 50.

## 3.2 Pushbutton class

This can support normally open or normally closed switches, connected to ``gnd``
(with a pullup) or to ``3V3`` (with a pull-down). The ``Pin`` object should be
initialised appropriately. The assumption is that on initialisation the button
is not pressed.

The Pushbutton class uses logical rather than physical state: a button's state
is considered ``True`` if pressed, otherwise ``False`` regardless of its
physical implementation.

Constructor argument (mandatory):

 1. ``pin`` The initialised Pin instance.

Methods:

 1. ``press_coro`` Args: ``coro`` (mandatory) a coro to run on button push.
 ``args`` a tuple of arguments for the coro (default ())
 2. ``release_coro`` Args: ``coro`` (mandatory) a coro to run on button release.
 ``args`` a tuple of arguments for the coro (default ())
 3. ``long_coro`` Args: ``coro`` (mandatory) a coro to run on long button push.
 ``args`` a tuple of arguments for the coro (default ())
 4. ``double_coro`` Args: ``coro`` (mandatory) a coro to run on double push.
 ``args`` a tuple of arguments for the coro (default ())
 5. ``__call__`` Call syntax e.g. ``mybutton()`` Returns the logical debounced
 state of the button (``True`` corresponds to pressed).
 6. ``rawstate()`` Returns the logical instantaneous state of the button. There
 is probably no reason to use this.

Class attributes:
 1. ``debounce_ms`` Debounce time in ms. Default 50.
 2. ``long_press_ms`` Threshold time in ms for a long press. Default 1000.
 3. ``double_click_ms`` Threshold time in ms for a double click. Default 400.

## 3.3 Delay_ms class

This implements the software equivalent of a retriggerable monostable or a
watchdog timer. It has a boolean ``running`` state. When instantiated it does
nothing, with ``running`` ``False`` until triggered, when ``running`` becomes
``True``. A timer is then initiated. This can be prevented from timing out by
triggering it again (with a new timeout duration). So long as it is triggered
before the time specified in the preceeding trigger it will never time out.

If it does time out the ``running`` state will revert to ``False``. This can be
interrogated by the object's ``running()`` method. In addition a coro can be
specified to the constructor. This will be scheduled for execution when a
timeout occurs.

Constructor arguments (defaults in brackets):

 1. ``coro`` The coro to run on timeout (default ``None``).
 2. ``coro_args`` A tuple of arguments for the coro (default ``()``).

Methods:

 1. ``trigger`` mandatory argument ``duration``. A timeout will occur after
 ``duration`` ms unless retriggered.
 2. ``stop`` No argument. Cancels the timeout, setting the ``running`` status
 ``False``. The timer can be restarted by issuing ``trigger`` again.
 3. ``running`` No argument. Returns the running status of the object.

# 4. Module astests.py

This provides demonstration/test functions for the ``Switch`` and ``Pushbutton``
classes. They assume a switch or button wired between pin X1 and gnd.

## 4.1 Function test_sw()

This will flash the red LED on switch closure, and the green LED on opening.

### 4.1.1 Race conditions

Note that if the switch is cycled rapidly the LED behaviour may seem surprising.
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

## 4.2 Function test_btn()

This will flash the red LED on button push, and the green LED on release. A
long press will flash the blue LED and a double-press the yellow one.

The above note on race conditions applies.
