# A communication link using I2C

This library implements an asynchronous bidirectional communication link
between MicroPython targets using I2C. It presents a UART-like interface
supporting `StreamReader` and `StreamWriter` classes. In doing so, it emulates
the behaviour of a full duplex link despite the fact that the underlying I2C
link is half duplex.

One use case is to provide a UART-like interface to an ESP8266 while leaving
the one functional UART free for the REPL.

The blocking nature of the MicroPython I2C device driver is mitigated by
hardware synchronisation on two wires. This ensures that the slave is
configured for a transfer before the master attempts to access it.

The Pyboard or similar STM based boards are currently the only targets
supporting I2C slave mode. Consequently at least one end of the interface
(known as the`Initiator`) must be a Pyboard. The other end may be any hardware
running MicroPython.

The `Initiator` implements a timeout enabling it to detect failure of the other
end of the interface (the `Responder`). There is optional provision to reset
the `Responder` in this event.

## Changes

V0.15 RAM allocation reduced and flow control implemented.
V0.1 Initial release.

###### [Main README](../README.md)

# Contents

 1. [Files](./README.md#1-files)  
 2. [Wiring](./README.md#2-wiring)  
 3. [Design](./README.md#3-design)  
 4. [API](./README.md#4-api)  
  4.1 [Channel class](./README.md#41-channel-class)  
  4.2 [Initiator class](./README.md#42-initiator-class)  
    4.2.1 [Configuration](./README.md#421-configuration) Fine-tuning the interface.  
  4.3 [Responder class](./README.md#43-responder-class)  
 5. [Limitations](./README.md#5-limitations)  
  5.1 [Blocking](./README.md#51-blocking)  
  5.2 [Buffering and RAM usage](./README.md#52-buffering-and-ram-usage)  
  5.3 [Responder crash detection](./README.md#53-responder-crash-detection)  

# 1. Files

 1. `asi2c.py` Module for the `Responder` target.
 2. `asi2c_i.py` The `Initiator` target requires this and `asi2c.py`.
 3. `i2c_init.py` Initiator test/demo to run on a Pyboard.
 4. `i2c_resp.py` Responder test/demo to run on a Pyboard.
 5. `i2c_esp.py` Responder test/demo for ESP8266.

Dependency:  
 1. `uasyncio` Official library or my fork.

# 2. Wiring

| Pyboard | Target | Comment |
|:-------:|:------:|:-------:|
|  gnd    |  gnd   |         |
|  sda    |  sda   | I2C     |
|  scl    |  scl   | I2C     |
|  sync   |  sync  | Any pin may be used. |
|  ack    |  ack   | Any pin. |
|  rs_out |  rst   | Optional reset link. |

The `sync` and `ack` wires provide synchronisation: pins used are arbitrary. In
addition provision may be made for the Pyboard to reset the target if it
crashes and fails to respond. If this is required, link a Pyboard pin to the
target's `reset` pin.

I2C requires the devices to be connected via short links and to share a common
ground. The `sda` and `scl` lines also require pullup resistors. On the Pyboard
V1.x these are fitted. If pins lacking these resistors are used, pullups to
3.3V should be supplied. A typical value is 4.7KΩ.

###### [Contents](./README.md#contents)

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
under application control and may be as low as 100ms.

The module will run under official or `fast_io` builds of `uasyncio`. Owing to
the latency discussed above the performance of this interface is largely
unaffected.

A further issue common to most communications protocols is synchronisation:
the devices won't boot simultaneously. Initially, and after the `Initiator`
reboots the `Responder`, both ends run a synchronisation phase. The iterface
starts to run once each end has determined that its counterpart is ready.

The design assumes exclusive use of the I2C interface. Hard or soft I2C may be
used.

###### [Contents](./README.md#contents)

# 4. API

The following is a typical `Initiator` usage example where the two participants
exchange Python objects serialised using `ujson`:

```python
import uasyncio as asyncio
from pyb import I2C  # Only pyb supports slave mode
from machine import Pin
import asi2c
import ujson

i2c = I2C(1, mode=I2C.SLAVE)  # Soft I2C may be used
syn = Pin('X11')  # Pins are arbitrary but must be declared
ack = Pin('Y8')  # using machine
rst = (Pin('X12'), 0, 200)  # Responder reset is low for 200ms
chan = asi2c.Initiator(i2c, syn, ack, rst)

async def receiver():
    sreader = asyncio.StreamReader(chan)
    while True:
        res = await sreader.readline()
        print('Received', ujson.loads(res))

async def sender():
    swriter = asyncio.StreamWriter(chan, {})
    txdata = [0, 0]
    while True:
        await swriter.awrite(''.join((ujson.dumps(txdata), '\n')))
        txdata[0] += 1
        await asyncio.sleep_ms(800)
```

Code for `Responder` is very similar. See `i2c_init.py` and `i2c_resp.py` for
complete examples.

###### [Contents](./README.md#contents)

## 4.1 Channel class

This is the base class for `Initiator` and `Responder` subclasses and provides
support for the streaming API. Applications do not instantiate `Channel`
objects.

Method:
 1. `close` No args. Restores the interface to its power-up state.
 
Coroutine:
 1. `ready` No args. Pause until synchronisation has been achieved.

## 4.2 Initiator class

Constructor args:  
 1. `i2c` An `I2C` instance.
 2. `pin` A `Pin` instance for the `sync` signal.
 3. `pinack` A `Pin` instance for the `ack` signal.
 4. `reset=None` Optional tuple defining a reset pin (see below).
 5. `verbose=True` If `True` causes debug messages to be output.

The `reset` tuple consists of (`pin`, `level`, `time`). If provided, and the
`Responder` times out, `pin` will be set to `level` for duration `time` ms. A
Pyboard or ESP8266 target with an active low reset might have:

```python
(machine.Pin('X12'), 0, 200)
```

If the `Initiator` has no `reset` tuple and the `Responder` times out, an
`OSError` will be raised.

`Pin` instances passed to the constructor must be instantiated by `machine`.

Class variables:
 1. `timeout=1000` Timeout (in ms) before `Initiator` assumes `Responder` has
 failed.
 2. `t_poll=100` Interval (ms) for `Initiator` polling `Responder`.
 3. `rxbufsize=200` Size of receive buffer. This should exceed the maximum
 message length.

Class variables should be set before instantiating `Initiator` or `Responder`.
See [Section 4.4](./README.md#44-configuration).

Instance variables:

The `Initiator` maintains instance variables which may be used to measure its
peformance. See [Section 4.4](./README.md#44-configuration).

Coroutine:
 1. `reboot` If a `reset` tuple was provided, reboot the `Responder`.

## 4.2.1 Configuration

The `Initiator` class variables determine the behaviour of the interface. Where
these are altered, it should be done before instantiation.

`Initiator.timeout` If the `Responder` fails the `Initiator` times out and
resets the `Responder`; this occurs if `reset` tuple with a pin is supplied.
Otherwise the `Initiator` raises an `OSError`.

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

###### [Contents](./README.md#contents)

## 4.3 Responder class

Constructor args:
 1. `i2c` An `I2C` instance.
 2. `pin` A `Pin` instance for the `sync` signal.
 3. `pinack` A `Pin` instance for the `ack` signal.
 4. `verbose=True` If `True` causes debug messages to be output.

`Pin` instances passed to the constructor must be instantiated by `machine`.

Class variables:
 1. `addr=0x12` Address of I2C slave. This should be set before instantiating
 `Initiator` or `Responder`. If the default address (0x12) is to be overriden,
 `Initiator` application code must instantiate the I2C accordingly.
 2. `rxbufsize` Size of receive buffer. This should exceed the maximum message
 length.

###### [Contents](./README.md#contents)

# 5. Limitations

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

I tried a variety of approaches before settling on a synchronous method for
data exchange coupled with 2-wire hardware handshaking. The chosen approach
minimises the time for which the schedulers are blocked. This is because of
the need to initiate a blocking transfer on the I2C slave before the master can
initiate a transfer. A one-wire handshake using open drain outputs is feasible
but involves explicit delays. I took the view that a 2-wire solution is easier
should anyone want to port the `Responder` to a platform such as the Raspberry
Pi. The design has no timing constraints and uses normal I/O pins.

## 5.2 Buffering and RAM usage

The protocol implements flow control: the `StreamWriter` at one end of the link
will pause until the last string transmitted has been read by the corresponding
`StreamReader`.

Outgoing data is unbuffered. `StreamWriter.awrite` will pause until pending
data has been transmitted.

Efforts are under way to remove RAM allocation by the `Responder`. This would
enable hard interrupts to be used, further reducing blocking. With this aim
incoming data is buffered in a pre-allocated bytearray.

## 5.3 Responder crash detection

The `Responder` protocol executes in a soft interrupt context. This means that
the application code might fail (for example executing an infinite loop) while
the ISR continues to run; `Initiator` would therefore see no problem. To trap
this condition regular messages should be sent from `Responder`, with
`Initiator` application code timing out on their absence and issuing `reboot`.

###### [Contents](./README.md#contents)
