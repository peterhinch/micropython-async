# Communication between MicroPython hardware boards

This provides a means of communication between two devices, each running
MicroPython, where a UART cannot be used. An example is where one device is an
ESP8266 board. While this has one bidirectional UART, this may be in use either
as a REPL console, for viewing debug output, or for other puposes.

It is intended for use in asynchronous programs and uses uasyncio.

The module offers a bidirectional full duplex communication channel between two
hardware devices. Its unit of communication is an arbitrary Python object
making for simple application. In an alternative mode for resource constrained
devices, the unit of communication is a string.

Physically it uses a 4-wire interface plus an additional wire to enable the
host to issue a hardware reset to the target in the event that the target
crashes or becomes unresponsive. Where the target is an ESP8266 this can occur
for various reasons including network issues where sockets can block
indefinitely.

The module will run on devices with minimal features and makes no assumptions
about processing performance: at a physical level the interface is synchronous.
If each device has two pins which can be used for output and two for input and
supports uasyncio it should work.

###### [Main README](./README.md)

## Example usage

```python
import uasyncio as asyncio
from syncom import SynCom
from machine import Pin

 # Task just echoes objects back
async def passive_task(chan):
    while True:
        obj = await chan.await_obj()
        chan.send(obj)

mtx = Pin(14, Pin.OUT, value = 0)    # Define pins
mckout = Pin(15, Pin.OUT, value = 0) # clock must be initialised to zero.
mrx = Pin(13, Pin.IN)
mckin = Pin(12, Pin.IN)

channel = SynCom(True, mckin, mckout, mrx, mtx)
try:
    asyncio.run(channel.start(passive_task))
except KeyboardInterrupt:
    pass
finally:
    mckout(0)  # For a subsequent run
    _ = asyncio.new_event_loop()
```

## Advantages

 * Readily portable to any MicroPython platform.
 * It does not use hardware features such as interrupts or timers.
 * Hardware requirement: two arbitrary output pins and two input pins on each
 device.
 * The interface is synchronous, having no timing dependencies.
 * It supports full duplex communications (concurrent send and receive).
 * The unit of transmission is an arbitrary Python object.
 * All methods are non-blocking.
 * Small: <200 lines of Python.

## Limitations

 * The interface is an alternative to I2C or SPI and is intended for directly
 linked devices sharing a common power supply.
 * It is slow. With a Pyboard linked to an ESP8266 clocked at 160MHz, the
 peak bit rate is 1.6Kbps. Mean throughput is about 800bps.
 In practice throughput will depend on the performance of the slowest device
 and the behaviour of other tasks.

## Rationale

The obvious question is why not use I2C or SPI. The reason is the nature of the
slave interfaces: these protocols are designed for the case where the slave is
a hardware device which guarantees a timely response. The MicroPython slave
drivers achieve this by means of blocking system calls. Synchronising master
and slave is difficult because the master needs to ensure that the slave is
running the blocking call before transmitting. For the slave to do anything
useful the code must be designed to ensure that the call exits at the end of a
message.

Further such blocking calls are incompatible with asynchronous programming.

The two ends of the link are defined as `initiator` and `passive`. These
describe their roles in initialisation. Once running the protocol is
symmetrical and the choice as to which unit to assign to each role is
arbitrary: the test programs assume that the Pyboard is the initiator.

# Files

 * syncom.py The library.
 * sr_init.py Test program configured for Pyboard: run with sr_passive.py on
 the other device.
 * sr_passive.py Test program configured for ESP8266: sr_init.py runs on other
 end of link.

# Hardware connections

Each device has the following logical connections, `din`, `dout`, `ckin`,
`ckout`. The `din` (data in) of one device is linked to `dout` (data out)
of the other, and vice versa. Likewise the clock signals `ckin` and `ckout`.

To enable a response to crash detection a pin on the Pyboard is connected to
the Reset pin on the target. The polarity of the reset pulse is assumed to be
active low.

| Initiator   | Passive     | Pyboard | ESP8266 |
|:-----------:|:-----------:|:-------:|:-------:|
| reset (o/p) | reset (i/p) |   Y4    |  reset  |
| dout  (o/p) | din   (i/p) |   Y5    |   14    |
| ckout (o/p) | ckin  (i/p) |   Y6    |   15    |
| din   (i/p) | dout  (o/p) |   Y7    |   13    |
| ckin  (i/p) | ckout (o/p) |   Y8    |   12    |


# class SynCom

A SynCom instance is idle until its `start` task is scheduled. The driver
causes the host device to resets the target and wait for synchronisation. When
the interface is running the passed user task is launched; unless an error
occurs this runs forever using the interface as required by the application. If
crash detection is required the user task should check for a timeout. In this
event the user task should return. This causes the target to be reset and the
interface to re-synchronise. The user task is then re-launched.

## Constructor

Positional arguments:

 1. `passive` Boolean. One end of the link sets this `True`, the other
 `False`.
 2. `ckin` An initialised input `Pin` instance.
 3. `ckout` An initialised output `Pin` instance. It should be set to zero.
 4. `din` An initialised input `Pin` instance.
 5. `dout` An initialised output `Pin` instance.
 6. `sig_reset` (optional) default `None`. A `Pin` instance.
 7. `timeout` (optional) default 0. Units ms. See below.
 8. `string_mode` (optional) default `False`. See String Mode below.
 9. `verbose` (optional) default `True`. If set, debug messages will be
 output to the REPL.

## Synchronous Methods

 * `send` Argument an arbitrary Python object (or a string in string mode).
 Puts the item on the queue for transmission.
 * `any` No args.  
 Returns the number of received objects on the receive queue.
 * `running` No args.  
 Returns `True` if the channel is running, `False` if the target has timed
 out.

## Asynchronous Methods (tasks)

 * `await_obj` Argument `t_ms` default 10ms. See below.  
 Wait for reception of a Python object or string and return it. If the
 interface times out (because the target has crashed) return `None`.
 * `start` Optional args `user_task`, `fail_delay`.  
 Starts the interface. If a user_task is provided this will be launched when
 synchronisation is achived. The user task should return if a timeout is
 detected (by `await_obj` returning `None`). On return the driver will wait
 for `fail_delay` (see below) before asserting the reset signal to reset the
 target. The user task will be re-launched when synchronisation is achieved.
 The user_task is passed a single argument: the SynCom instance. If the user
 task is a bound method it should therefore be declared as taking two args:
 `self` and the channel.

The `fail_delay` (in seconds) is a convenience to allow user tasks to
terminate before the user task is restarted. On detection of a timeout an
application should set a flag to cause tasks instantiated by the user task to
terminate, then issue `return`. This avoids unlimited growth of the task
queue.

The `t_ms` argument to `await_obj` determines how long the task pauses
between checks for received data. Longer intervals increase latency but
(possibly) improve raw throughput.

# Notes

## Synchronisation

When the host launches the `start` coroutine it runs forever. It resets the
target which instantiates a SynCom object and launches its `start` coroutine.
The two then synchronise by repeatedly transmitting a `_SYN` character. Once
this has been received the link is synchronised and the user task is launched.

The user task runs forever on the target. On the host it may return if a target
timeout is detected. In this instance the host's `start` task waits for the
optional `fail_delay` before resetting the target and re-synchronising the
interface. The user task, which ran to completion, is re-launched.

## String Mode

By default `ujson` is used to serialise data. This can be avoided by sending
strings to the remote platform, which must then interpret the strings as
required by the application. The protocol places some restrictions. The bytes
must not include 0, and they are limited to 7 bits. The latter limitation can
be removed (with small performance penalty) by changing the value of
`_BITS_PER_CH` to 8. The limitations allow for normal UTF8 strings.

## Timing

The timing measurements in Limitations above were performed as follows. A logic
analyser was connected to one of the clock signals and the time for one
character (7 bits) to be transferred was measured (note that a bit is
transferred on each edge of the clock). This produced figures for the raw bits
per second throughput of the bitbanged interface.

The value produced by the test programs (sr_init.py and sr_passive.py) is the
total time to send an object and receive it having been echoed back by the
ESP8266. This includes encoding the object as a string, transmitting it,
decoding and modifying it, followed by similar processing to send it back.
Hence converting the figures to bps will produce a lower figure (on the order
of 656bps at 160MHz).
