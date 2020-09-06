# Decoder for IR Remote Controls using the NEC protocol

This protocol is widely used. An example remote is [this one](https://www.adafruit.com/products/389).
To interface the device a receiver chip such as the Vishay TSOP4838 or the
[adafruit one](https://www.adafruit.com/products/157) is required. This
demodulates the 38KHz IR pulses and passes the demodulated pulse train to the
microcontroller.

The driver and test programs run on the Pyboard and ESP8266.

# Files

 1. `aremote.py` The device driver.
 2. `art.py` A test program to characterise a remote.
 3. `art1.py` Control an onboard LED using a remote. The data and addresss
 values need changing to match your characterised remote.

# Dependencies

The driver requires the `uasyncio` library and the file `asyn.py` from this
repository.

# Usage

The pin used to connect the decoder chip to the target is arbitrary but the
test programs assume pin X3 on the Pyboard and pin 13 on the ESP8266.

The driver is event driven. Pressing a button on the remote causes a user
defined callback to be run. The NEC protocol returns a data value and an
address. These are passed to the callback as the first two arguments (further
user defined arguments may be supplied). The address is normally constant for a
given remote, with the data corresponding to the button. Applications should
check the address to ensure that they only respond to the correct remote.

Data values are 8 bit. Addresses may be 8 or 16 bit depending on whether the
remote uses extended addressing.

If a button is held down a repeat code is sent. In this event the driver
returns a data value of `REPEAT` and the address associated with the last
valid data block.

To characterise a remote run `art.py` and note the data value for each button
which is to be used. If the address is less than 256, extended addressing is
not in use.

# Reliability

IR reception is inevitably subject to errors, notably if the remote is operated
near the limit of its range, if it is not pointed at the receiver or if its
batteries are low. So applications must check for, and usually ignore, errors.
These are flagged by data values < `REPEAT`.

On the ESP8266 there is a further source of errors. This results from the large
and variable interrupt latency of the device which can exceed the pulse
duration. This causes pulses to be missed. This tendency is slightly reduced by
running the chip at 160MHz.

In general applications should provide user feedback of correct reception.
Users tend to press the key again if no acknowledgement is received.

# The NEC_IR class

The constructor takes the following positional arguments.

 1. `pin` A `Pin` instance for the decoder chip.
 2. `cb` The user callback function.
 3. `extended` Set `False` to enable extra error checking if the remote
 returns an 8 bit address.
 4. Further arguments, if provided, are passed to the callback.

The callback receives the following positional arguments:

 1. The data value returned from the remote.
 2. The address value returned from the remote.
 3. Any further arguments provided to the `NEC_IR` constructor.

Negative data values are used to signal repeat codes and transmission errors.

The test program `art1.py` provides an example of a minimal application.

# How it works

The NEC protocol is described in these references.  
[altium](http://techdocs.altium.com/display/FPGA/NEC+Infrared+Transmission+Protocol)  
[circuitvalley](http://www.circuitvalley.com/2013/09/nec-protocol-ir-infrared-remote-control.html)

A normal burst comprises exactly 68 edges, the exception being a repeat code
which has 4. An incorrect number of edges is treated as an error. All bursts
begin with a 9ms pulse. In a normal code this is followed by a 4.5ms space; a
repeat code is identified by a 2.25ms space. A data burst lasts for 67.5ms.

Data bits comprise a 562.5µs mark followed by a space whose length determines
the bit value. 562.5µs denotes 0 and 1.6875ms denotes 1.

In 8 bit address mode the complement of the address and data values is sent to
provide error checking. This also ensures that the number of 1's and 0's in a
burst is constant, giving a constant burst length of 67.5ms. In extended
address mode this constancy is lost. The burst length can (by my calculations)
run to 76.5ms.

A pin interrupt records the time of every state change (in µs). The first
interrupt in a burst sets an event, passing the time of the state change. A
coroutine waits on the event, yields for the duration of a data burst, then
decodes the stored data before calling the user-specified callback.

Passing the time to the `Event` instance enables the coro to compensate for
any asyncio latency when setting its delay period.

The algorithm promotes interrupt handler speed over RAM use: the 276 bytes used
for the data array could be reduced to 69 bytes by computing and saving deltas
in the interrupt service routine.

# Error returns

Data values passed to the callback are normally positive. Negative values
indicate a repeat code or an error.

`REPEAT` A repeat code was received.

Any data value < `REPEAT` denotes an error. In general applications do not
need to decode these, but they may be of use in debugging. For completeness
they are listed below.

`BADSTART` A short (<= 4ms) start pulse was received. May occur due to IR
interference, e.g. from fluorescent lights. The TSOP4838 is prone to producing
200µs pulses on occasion, especially when using the ESP8266.  
`BADBLOCK` A normal data block: too few edges received. Occurs on the ESP8266
owing to high interrupt latency.  
`BADREP` A repeat block: an incorrect number of edges were received.  
`OVERRUN` A normal data block: too many edges received.  
`BADDATA` Data did not match check byte.  
`BADADDR` Where `extended` is `False` the 8-bit address is checked
against the check byte. This code is returned on failure.  
