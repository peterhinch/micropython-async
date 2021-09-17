# A communication link using I2C

This library implements an asynchronous bidirectional communication link
between MicroPython targets using I2C. It presents a UART-like interface
supporting `StreamReader` and `StreamWriter` classes. In doing so, it emulates
the behaviour of a full duplex link despite the fact that the underlying I2C
link is half duplex.

This version is for `uasyncio` V3 which requires firmware V1.13 or later -
until the release of V1.13 a daily build is required.

One use case is to provide a UART-like interface to an ESP8266 while leaving
the one functional UART free for the REPL.

The blocking nature of the MicroPython I2C device driver is mitigated by
hardware synchronisation on two wires. This ensures that the slave is
configured for a transfer before the master attempts to access it.

The Pyboard or similar STM based boards are currently the only targets
supporting I2C slave mode. Consequently at least one end of the interface
(known as the`Initiator`) must be a Pyboard or other board supporting the `pyb`
module. The `Responder` may be any hardware running MicroPython and supporting
`machine`.

If the `Responder` (typically an ESP8266) crashes the resultant I2C failure is
detected by the `Initiator` which can issue a hardware reboot to the 
`Responder` enabling the link to recover. This can occur transparently to the
application and is covered in detail
[in section 5.3](./I2C.md#53-responder-crash-detection).

## Changes

V0.18 Apr 2020 Ported to `uasyncio` V3. Convert to Python package. Test script
pin numbers changed to be WBUS_DIP28 fiendly.  
V0.17 Dec 2018 Initiator: add optional "go" and "fail" user coroutines.  
V0.16 Minor improvements and bugfixes. Eliminate `timeout` option which caused
failures where `Responder` was a Pyboard.  
V0.15 RAM allocation reduced. Flow control implemented.  
V0.1 Initial release.

###### [Main README](../README.md)

# Contents

 1. [Files](./I2C.md#1-files)  
 2. [Wiring](./I2C.md#2-wiring)  
 3. [Design](./I2C.md#3-design)  
 4. [API](./I2C.md#4-api)  
  4.1 [Channel class](./I2C.md#41-channel-class)  
  4.2 [Initiator class](./I2C.md#42-initiator-class)  
    4.2.1 [Configuration](./I2C.md#421-configuration) Fine-tuning the interface.  
    4.2.2 [Optional coroutines](./I2C.md#422-optional-coroutines)  
  4.3 [Responder class](./I2C.md#43-responder-class)  
 5. [Limitations](./I2C.md#5-limitations)  
  5.1 [Blocking](./I2C.md#51-blocking)  
  5.2 [Buffering and RAM usage](./I2C.md#52-buffering-and-ram-usage)  
  5.3 [Responder crash detection](./I2C.md#53-responder-crash-detection)  
 6. [Hacker notes](./I2C.md#6-hacker-notes) For anyone wanting to hack on
 the code.

# 1. Files

 1. `asi2c.py` Module for the `Responder` target.
 2. `asi2c_i.py` The `Initiator` target requires this and `asi2c.py`.
 3. `i2c_init.py` Initiator test/demo to run on a Pyboard.
 4. `i2c_resp.py` Responder test/demo to run on a Pyboard.
 5. `i2c_esp.py` Responder test/demo for ESP8266.

#### Dependency:  
 1. `uasyncio` Official V3 library.

#### Installation  
Copy the `as_drivers/i2c` directory and contents to the target hardware.

###### [Main V3 README](../README.md)

# 2. Wiring

Pin numbers are for the test programs: these may be changed. I2C pin numbers
may be changed by using soft I2C. In each case except `rs_out`, the two targets
are connected by linking identically named pins.

ESP pins are labelled reference board pin no./WeMOS D1 Mini pin no.

| Pyboard | Target | PB  | ESP  | Comment |
|:-------:|:------:|:---:|:----:|:-------:|
|  gnd    |  gnd   |     |      |         |
|  sda    |  sda   | Y10 | 2/D4 | I2C     |
|  scl    |  scl   | Y9  | 0/D3 | I2C     |
|  syn    |  syn   | Y11 | 5/D1 | Any pin may be used. |
|  ack    |  ack   | X6  | 4/D2 | Any pin. |
|  rs_out |  rst   | Y12 |      | Optional reset link. |

The `syn` and `ack` wires provide synchronisation: pins used are arbitrary. In
addition provision may be made for the Pyboard to reset the target if it
crashes and fails to respond. If this is required, link a Pyboard pin to the
target's `reset` pin.

I2C requires the devices to be connected via short links and to share a common
ground. The `sda` and `scl` lines also require pullup resistors. On the Pyboard
V1.x these are fitted. If pins lacking these resistors are used, pullups to
3.3V should be supplied. A typical value is 4.7KΩ.

On the Pyboard D the 3.3V supply must be enabled with
```python
machine.Pin.board.EN_3V3.value(1)
```
This also enables the I2C pullups on the X side.

###### [Contents](./I2C.md#contents)

# 3. Design

The I2C specification is asymmetrical: only master devices can initiate
transfers. This library enables slaves to initiate a data exchange by
interrupting the master which then starts the I2C transactions. There is a
timing issue in that the I2C master requires that the slave be ready before it
initiates a transfer. Further, in the MicroPython implementation, a slave which
is ready will block until the transfer is complete.

To meet the timing constraint the slave must initiate all exchanges; it does
this by interrupting the master. The slave is therefore termed the `Initiator`
and the master `Responder`. The `Initiator` must be a Pyboard or other STM
board supporting slave mode via the `pyb` module.

To enable `Responder` to start an unsolicited data transfer, `Initiator`
periodically interrupts `Responder` to cause a data exchange. If either
participant has no data to send it sends an empty string. Strings are exchanged
at a fixed rate to limit the interrupt overhead on `Responder`. This implies a
latency on communications in either direction; the rate (maximum latency) is
under application control. By default it is 100ms.

The module will run under official or `fast_io` builds of `uasyncio`. Owing to
the latency discussed above, the choice has little effect on the performance of
this interface.

A further issue common to most communications protocols is synchronisation:
the devices won't boot simultaneously. Initially, and after the `Initiator`
reboots the `Responder`, both ends run a synchronisation phase. The interface
starts to run once each end has determined that its counterpart is ready.

The design assumes exclusive use of the I2C interface. Hard or soft I2C may be
used.

###### [Contents](./I2C.md#contents)

# 4. API

Demos and the scripts below assume a Pyboard linked to an ESP8266 as follows:

| Pyboard | ESP8266 | Notes    |
|:-------:|:-------:|:--------:|
|  gnd    |  gnd    |          |
|  Y9     |  0/D3   | I2C scl  |
|  Y10    |  2/D4   | I2C sda  |
|  Y11    |  5/D1   | syn      |
|  Y12    |  rst    | Optional |
|  X6     |  4/D2   | ack      |

#### Running the demos

On the ESP8266 issue:
```python
import as_drivers.i2c.i2c_esp
```
and on the Pyboard:
```python
import as_drivers.i2c.i2c_init
```

The following scripts demonstrate basic usage. They may be copied and pasted at
the REPL.  
On Pyboard:

```python
import uasyncio as asyncio
from pyb import I2C  # Only pyb supports slave mode
from machine import Pin
from as_drivers.i2c.asi2c_i import Initiator

i2c = I2C(2, mode=I2C.SLAVE)
syn = Pin('Y11')
ack = Pin('X6')
rst = (Pin('Y12'), 0, 200)
chan = Initiator(i2c, syn, ack, rst)

async def receiver():
    sreader = asyncio.StreamReader(chan)
    while True:
        res = await sreader.readline()
        print('Received', int(res))

async def sender():
    swriter = asyncio.StreamWriter(chan, {})
    n = 0
    while True:
        await swriter.awrite('{}\n'.format(n))
        n += 1
        await asyncio.sleep_ms(800)

asyncio.create_task(receiver())
try:
    asyncio.run(sender())
except KeyboardInterrupt:
    print('Interrupted')
finally:
    asyncio.new_event_loop()  # Still need ctrl-d because of interrupt vector
    chan.close()  # for subsequent runs
```

On ESP8266:

```python
import uasyncio as asyncio
from machine import Pin, I2C
from as_drivers.i2c.asi2c import Responder

i2c = I2C(scl=Pin(0),sda=Pin(2))  # software I2C
syn = Pin(5)
ack = Pin(4)
chan = Responder(i2c, syn, ack)

async def receiver():
    sreader = asyncio.StreamReader(chan)
    while True:
        res = await sreader.readline()
        print('Received', int(res))

async def sender():
    swriter = asyncio.StreamWriter(chan, {})
    n = 1
    while True:
        await swriter.awrite('{}\n'.format(n))
        n += 1
        await asyncio.sleep_ms(1500)

asyncio.create_task(receiver())
try:
    asyncio.run(sender())
except KeyboardInterrupt:
    print('Interrupted')
finally:
    asyncio.new_event_loop()  # Still need ctrl-d because of interrupt vector
    chan.close()  # for subsequent runs
```

###### [Contents](./I2C.md#contents)

## 4.1 Channel class

This is the base class for `Initiator` and `Responder` subclasses and provides
support for the streaming API. Applications do not instantiate `Channel`
objects.

Method:
 1. `close` No args. Restores the interface to its power-up state.
 
Coroutine:
 1. `ready` No args. Pause until synchronisation has been achieved.

## 4.2 Initiator class

##### Constructor args:  
 1. `i2c` An `I2C` instance.
 2. `pin` A `Pin` instance for the `syn` signal.
 3. `pinack` A `Pin` instance for the `ack` signal.
 4. `reset=None` Optional tuple defining a reset pin (see below).
 5. `verbose=True` If `True` causes debug messages to be output.
 6. `cr_go=False` Optional coroutine to run at startup. See
 [4.2.2](./I2C.md#422-optional-coroutines).
 7. `go_args=()` Optional tuple of args for above coro.
 8. `cr_fail=False` Optional coro to run on ESP8266 fail or reboot.
 9. `f_args=()` Optional tuple of args for above.

The `reset` tuple consists of (`pin`, `level`, `time`). If provided, and the
`Responder` times out, `pin` will be set to `level` for duration `time` ms. A
Pyboard or ESP8266 target with an active low reset might have:

```python
(machine.Pin('Y12'), 0, 200)
```

If the `Initiator` has no `reset` tuple and the `Responder` times out, an
`OSError` will be raised.

`Pin` instances passed to the constructor must be instantiated by `machine`.

##### Class variables:
 1. `t_poll=100` Interval (ms) for `Initiator` polling `Responder`.
 2. `rxbufsize=200` Size of receive buffer. This should exceed the maximum
 message length.

See [Section 4.2.1](./I2C.md#421-configuration).

##### Instance variables:

The `Initiator` maintains instance variables which may be used to measure its
peformance. See [Section 4.2.1](./I2C.md#421-configuration).

##### Coroutine:
 1. `reboot` If a `reset` tuple was provided, reboot the `Responder`.

## 4.2.1 Configuration

The `Initiator` class variables determine the behaviour of the interface. Where
these are altered, it should be done before  instantiating `Initiator` or
`Responder`.

`Initiator.t_poll` This defines the polling interval for incoming data. Shorter
values reduce the latency when the `Responder` sends data; at the cost of a
raised CPU overhead (at both ends) in processing `Responder` polling.

Times are in ms.

To measure performance when running application code these `Initiator` instance
variables may be read:
 1. `nboots` Number of times `Responder` has failed and been rebooted.
 2. `block_max` Maximum blocking time in μs.
 3. `block_sum` Cumulative total of blocking time (μs).
 4. `block_cnt` Transfer count: mean blocking time is `block_sum/block_cnt`.

See test program `i2c_init.py` for an example of using the above.

## 4.2.2 Optional coroutines

These are intended for applications where the `Responder` may reboot at runtime
either because I2C failure was detected or because the application issues an
explicit reboot command.

The `cr_go` and `cr_fail` coroutines provide for applications which implement
an application-level initialisation sequence on first and subsequent boots of
the `Responder`. Such applications need to ensure that the initialisation
sequence does not conflict with other coros accessing the channel.

The `cr_go` coro runs after synchronisation has been achieved. It runs
concurrently with the coro which keeps the link open (`Initiator._run()`), but
should run to completion reasonably quickly. Typically it performs any app
level synchronisation, starts or re-enables application coros, and quits.

The `cr_fail` routine will prevent the automatic reboot from occurring until
it completes. This may be used to prevent user coros from accessing the channel
until reboot is complete. This may be done by means of locks or task
cancellation. Typically `cr_fail` will terminate when this is done, so that
`cr_go` has unique access to the channel.

If an explicit `.reboot()` is issued, a reset tuple was provided, and `cr_fail`
exists, it will run and the physical reboot will be postponed until it
completes.

Typical usage:
```python
from as_drivers.i2c.asi2c_i import Initiator
chan = Initiator(i2c, syn, ack, rst, verbose, self._go, (), self._fail)
```

###### [Contents](./I2C.md#contents)

## 4.3 Responder class

##### Constructor args:
 1. `i2c` An `I2C` instance.
 2. `pin` A `Pin` instance for the `syn` signal.
 3. `pinack` A `Pin` instance for the `ack` signal.
 4. `verbose=True` If `True` causes debug messages to be output.

`Pin` instances passed to the constructor must be instantiated by `machine`.

##### Class variables:
 1. `addr=0x12` Address of I2C slave. If the default address is to be changed,
 it should be set before instantiating `Initiator` or `Responder`. `Initiator`
 application code must then instantiate the I2C accordingly.
 2. `rxbufsize=200` Size of receive buffer. This should exceed the maximum
 message length. Consider reducing this in ESP8266 applications to save RAM.

###### [Contents](./I2C.md#contents)

# 5. Limitations

Currently, on the ESP8266, the code is affected by
[iss 5714](https://github.com/micropython/micropython/issues/5714). Unless the
board is repeatedly pinged, the ESP8266 fails periodically and is rebooted by
the Pyboard.

## 5.1 Blocking

Exchanges of data occur via `Initiator._sendrx()`, a synchronous method. This
blocks the schedulers at each end for a duration dependent on the number of
bytes being transferred. Tests were conducted with the supplied test scripts
and the official version of `uasyncio`. Note that these scripts send short
strings.

With `Responder` running on a Pyboard V1.1 the duration of the ISR was up to
1.3ms.

With `Responder` on an ESP8266 running at 80MHz, `Initiator` blocked for up to
10ms with a mean time of 2.7ms; at 160MHz the figures were 7.5ms and 2.1ms. The
ISR uses soft interrupts, and blocking commences as soon as the interrupt pin
is asserted. Consequently the time for which `Initiator` blocks depends on
`Responder`'s interrupt latency; this may be extended by garbage collection.

Figures are approximate: actual blocking time is dependent on the length of the
strings, the speed of the processors, soft interrupt latency and the behaviour
of other coroutines. If blocking time is critical it should be measured while
running application code.

## 5.2 Buffering and RAM usage

The protocol implements flow control: the `StreamWriter` at one end of the link
will pause until the last string transmitted has been read by the corresponding
`StreamReader`.

Outgoing data is unbuffered. `StreamWriter.awrite` will pause until pending
data has been transmitted.

Incoming data is stored in a buffer whose length is set by the `rxbufsize`
constructor arg. If an incoming payload is too long to fit the buffer a
`ValueError` will be thrown.

## 5.3 Responder crash detection

The `Responder` protocol executes in a soft interrupt context. This means that
the application code might fail (for example executing an infinite loop) while
the ISR continues to run; `Initiator` would therefore see no problem. To trap
this condition regular messages should be sent from `Responder`, with
`Initiator` application code timing out on their absence and issuing `reboot`.

This also has implications when testing. If a `Responder` application is
interrupted with `ctrl-c` the ISR will continue to run. To test crash detection
issue a soft or hard reset to the `Responder`.

###### [Contents](./I2C.md#contents)

# 6. Hacker notes

I tried a variety of approaches before settling on a synchronous method for
data exchange coupled with 2-wire hardware handshaking. The chosen approach
minimises the time for which the schedulers are blocked. Blocking occurs
because of the need to initiate a blocking transfer on the I2C slave before the
master can initiate a transfer.

A one-wire handshake using open drain outputs is feasible but involves explicit
delays. I took the view that a 2-wire solution is easier should anyone want to
port the `Responder` to a platform such as the Raspberry Pi. The design has no
timing constraints and uses normal push-pull I/O pins.

I experienced a couple of obscure issues affecting reliability. Calling `pyb`
`I2C` methods with an explicit timeout caused rare failures when the target was
also a Pyboard. Using `micropython.schedule` to defer RAM allocation also
provoked rare failures. This may be the reason why I never achieved reliable
operation with hard IRQ's on ESP8266.

I created a version which eliminated RAM allocation by the `Responder` ISR to
use hard interrupts. This reduced blocking further. Unfortunately I failed to
achieve reliable operation on an ESP8266 target. This version introduced some
complexity into the code so was abandoned. If anyone feels like hacking, the
branch `i2c_hard_irq` exists.

The main branch aims to minimise allocation while achieving reliability.

PR's to reduce allocation and enable hard IRQ's welcome. I will expect them to
run the two test programs for >10,000 messages with ESP8266 and Pyboard
targets. Something I haven't yet achieved (with hard IRQ's).
