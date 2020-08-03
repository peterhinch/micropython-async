# 1 as_GPS

This repository offers a suite of asynchronous device drivers for GPS devices
which communicate with the host via a UART. GPS [NMEA-0183] sentence parsing is
based on this excellent library [micropyGPS].

The code in this V3 repo has been ported to uasyncio V3. Some modules can run
under CPython: doing so will require Python V3.8 or later.

###### [Tutorial](./TUTORIAL.md#contents)  
###### [Main V3 README](../README.md)

## 1.1 Driver characteristics

 * Asynchronous: UART messaging is handled as a background task allowing the
 application to perform other tasks such as handling user interaction.
 * The read-only driver is suitable for resource constrained devices and will
 work with most GPS devices using a UART for communication.
 * Can write `.kml` files for displaying journeys on Google Earth.
 * The read-write driver enables altering the configuration of GPS devices
 based on the popular MTK3329/MTK3339 chips.
 * The above drivers are portable between [MicroPython] and Python 3.8 or above.
 * Timing drivers for [MicroPython] only extend the capabilities of the
 read-only and read-write drivers to provide accurate sub-ms GPS timing. On
 STM-based hosts (e.g. the Pyboard) the RTC may be set from GPS and calibrated
 to achieve timepiece-level accuracy.
 * Drivers may be extended via subclassing, for example to support additional
 sentence types.

Testing was performed using a [Pyboard] with the Adafruit
[Ultimate GPS Breakout] board. Most GPS devices will work with the read-only
driver as they emit [NMEA-0183] sentences on startup.

## 1.2 Comparison with [micropyGPS]

[NMEA-0183] sentence parsing is based on [micropyGPS] but with significant
changes.

 * As asynchronous drivers they require `uasyncio` on [MicroPython] or
 `asyncio` under Python 3.8+.
 * Sentence parsing is adapted for asynchronous use.
 * Rollover of local time into the date value enables worldwide use.
 * RAM allocation is cut by various techniques to lessen heap fragmentation.
 This improves application reliability on RAM constrained devices.
 * Some functionality is devolved to a utility module, reducing RAM usage where
 these functions are unused.
 * The read/write driver is a subclass of the read-only driver.
 * Timing drivers are added offering time measurement with μs resolution and
 high absolute accuracy. These are implemented by subclassing these drivers.
 * Hooks are provided for user-designed subclassing, for example to parse
 additional message types.

###### [Main V3 README](../README.md)

## 1.3 Overview

The `AS_GPS` object runs a coroutine which receives [NMEA-0183] sentences from
the UART and parses them as they arrive. Valid sentences cause local bound
variables to be updated. These can be accessed at any time with minimal latency
to access data such as position, altitude, course, speed, time and date.

###### [Top](./GPS.md#1-as_gps)

# 2 Installation

## 2.1 Wiring

These notes are for the Adafruit Ultimate GPS Breakout. It may be run from 3.3V
or 5V. If running the Pyboard from USB, GPS Vin may be wired to Pyboard V+. If
the Pyboard is run from a voltage >5V the Pyboard 3V3 pin should be used.

| GPS |  Pyboard   | Optional |
|:---:|:----------:|:--------:|
| Vin | V+ or 3V3  |          |
| Gnd | Gnd        |          |
| PPS | X3         |    Y     |
| Tx  | X2 (U4 rx) |          |
| Rx  | X1 (U4 tx) |    Y     |

This is based on UART 4 as used in the test programs; any UART may be used. The
UART Tx-GPS Rx connection is only necessary if using the read/write driver. The
PPS connection is required only if using the timing driver `as_tGPS.py`. Any
pin may be used.

On the Pyboard D the 3.3V output is switched. Enable it with the following
(typically in `main.py`):
```python
import time
machine.Pin.board.EN_3V3.value(1)
time.sleep(1)
```

## 2.2 Library installation

The library is implemented as a Python package. To install copy the following
directories and their contents to the target hardware:  
 1. `as_drivers/as_GPS`
 2. `primitives`

On platforms with an underlying OS such as the Raspberry Pi ensure that the
directories are on the Python path and that the Python version is 3.8 or later.
Code samples will need adaptation for the serial port.

## 2.3 Dependency

The library requires `uasyncio` V3 on MicroPython and `asyncio` on CPython.

###### [Top](./GPS.md#1-as_gps)

# 3 Basic Usage

In the example below a UART is instantiated and an `AS_GPS` instance created.
A callback is specified which will run each time a valid fix is acquired.
The test runs for 60 seconds once data has been received.

```python
import uasyncio as asyncio
import as_drivers.as_GPS as as_GPS
from machine import UART
def callback(gps, *_):  # Runs for each valid fix
    print(gps.latitude(), gps.longitude(), gps.altitude)

uart = UART(4, 9600)
sreader = asyncio.StreamReader(uart)  # Create a StreamReader
gps = as_GPS.AS_GPS(sreader, fix_cb=callback)  # Instantiate GPS

async def test():
    print('waiting for GPS data')
    await gps.data_received(position=True, altitude=True)
    await asyncio.sleep(60)  # Run for one minute

asyncio.run(test())
```

This example achieves the same thing without using a callback:

```python
import uasyncio as asyncio
import as_drivers.as_GPS as as_GPS
from machine import UART

uart = UART(4, 9600)
sreader = asyncio.StreamReader(uart)  # Create a StreamReader
gps = as_GPS.AS_GPS(sreader)  # Instantiate GPS

async def test():
    print('waiting for GPS data')
    await gps.data_received(position=True, altitude=True)
    for _ in range(10):
        print(gps.latitude(), gps.longitude(), gps.altitude)
        await asyncio.sleep(2)

asyncio.run(test())
```

## 3.1 Demo programs

This assumes a Pyboard 1.x or Pyboard D with GPS connected to UART 4 and prints
received data:
```python
import as_drivers.as_gps.ast_pb
```

A simple demo which logs a route travelled to a .kml file which may be
displayed on Google Earth. Logging stops when the user switch is pressed.
Data is logged to `/sd/log.kml` at 10s intervals.
```python
import as_drivers.as_gps.log_kml
```

###### [Top](./GPS.md#1-as_gps)

# 4. The AS_GPS Class read-only driver

Method calls and access to bound variables are nonblocking and return the most
current data. This is updated transparently by a coroutine. In situations where
updates cannot be achieved, for example in buildings or tunnels, values will be
out of date. The action to take (if any) is application dependent.

Three mechanisms exist for responding to outages.  
 * Check the `time_since_fix` method [section 2.2.3](./GPS.md#423-time-and-date).
 * Pass a `fix_cb` callback to the constructor (see below).
 * Cause a coroutine to pause until an update is received: see
 [section 4.3.1](./GPS.md#431-data-validity). This ensures current data.

## 4.1 Constructor

Mandatory positional arg:
 * `sreader` This is a `StreamReader` instance associated with the UART.
Optional positional args:
 * `local_offset` Local timezone offset in hours realtive to UTC (GMT). May be
 an integer or float.
 * `fix_cb` An optional callback. This runs after a valid message of a chosen
 type has been received and processed.
 * `cb_mask` A bitmask determining which sentences will trigger the callback.
 Default `RMC`: the callback will occur on RMC messages only (see below).
 * `fix_cb_args` A tuple of args for the callback (default `()`).

Notes:  
`local_offset` will alter the date when time passes the 00.00.00 boundary.  
If `sreader` is `None` a special test mode is engaged (see `astests.py`).

### 4.1.1 The fix callback

This receives the following positional args:
 1. The GPS instance.
 2. An integer defining the message type which triggered the callback.
 3. Any args provided in `msg_cb_args`.

Message types are defined by the following constants in `as_GPS.py`: `RMC`,
`GLL`, `VTG`, `GGA`, `GSA` and `GSV`.

The `cb_mask` constructor argument may be the logical `or` of any of these
constants. In this example the callback will occur after successful processing
of RMC and VTG messages:

```python
gps = as_GPS.AS_GPS(sreader, fix_cb=callback, cb_mask= as_GPS.RMC | as_GPS.VTG)
```

## 4.2 Public Methods

### 4.2.1 Location

 * `latitude` Optional arg `coord_format=as_GPS.DD`. Returns the most recent
 latitude.  
 If `coord_format` is `as_GPS.DM` returns a tuple `(degs, mins, hemi)`.  
 If `as_GPS.DD` is passed returns `(degs, hemi)` where degs is a float.  
 If `as_GPS.DMS` is passed returns `(degs, mins, secs, hemi)`.  
 `hemi` is 'N' or 'S'.

 * `longitude` Optional arg `coord_format=as_GPS.DD`. Returns the most recent
 longitude.  
 If `coord_format` is `as_GPS.DM` returns a tuple `(degs, mins, hemi)`.  
 If `as_GPS.DD` is passed returns `(degs, hemi)` where degs is a float.  
 If `as_GPS.DMS` is passed returns `(degs, mins, secs, hemi)`.  
 `hemi` is 'E' or 'W'.

 * `latitude_string` Optional arg `coord_format=as_GPS.DM`. Returns the most
 recent  latitude in human-readable format. Formats are `as_GPS.DM`,
 `as_GPS.DD`, `as_GPS.DMS` or `as_GPS.KML`.  
 If `coord_format` is `as_GPS.DM` it returns degrees, minutes and hemisphere
 ('N' or 'S').
 `as_GPS.DD` returns degrees and hemisphere.  
 `as_GPS.DMS` returns degrees, minutes, seconds and hemisphere.  
 `as_GPS.KML` returns decimal degrees, +ve in northern hemisphere and -ve in
 southern, intended for logging to Google Earth compatible kml files.

 * `longitude_string` Optional arg `coord_format=as_GPS.DM`. Returns the most
 recent longitude in human-readable format. Formats are `as_GPS.DM`,
 `as_GPS.DD`, `as_GPS.DMS` or `as_GPS.KML`.  
 If `coord_format` is `as_GPS.DM` it returns degrees, minutes and hemisphere
 ('E' or 'W').
 `as_GPS.DD` returns degrees and hemisphere.  
 `as_GPS.DMS` returns degrees, minutes, seconds and hemisphere.  
 `as_GPS.KML` returns decimal degrees, +ve in eastern hemisphere and -ve in
 western, intended for logging to Google Earth compatible kml files.

### 4.2.2 Course

 * `speed` Optional arg `unit=as_GPS.KPH`. Returns the current speed in the
 specified units. Options: `as_GPS.KPH`, `as_GPS.MPH`, `as_GPS.KNOT`.

 * `speed_string` Optional arg `unit=as_GPS.KPH`. Returns the current speed in
 the specified units. Options `as_GPS.KPH`, `as_GPS.MPH`, `as_GPS.KNOT`.

 * `compass_direction` No args. Returns current course as a string e.g. 'ESE'
 or 'NW'. Note that this requires the file `as_GPS_utils.py`.

### 4.2.3 Time and date

 * `time_since_fix` No args. Returns time in milliseconds since last valid fix.

 * `time_string` Optional arg `local=True`. Returns the current time in form
 'hh:mm:ss.sss'. If `local` is `False` returns UTC time. 

 * `date_string` Optional arg `formatting=MDY`. Returns the date as
 a string. Formatting options:  
 `as_GPS.MDY` returns 'MM/DD/YY'.  
 `as_GPS.DMY` returns 'DD/MM/YY'.  
 `as_GPS.LONG` returns a string of form 'January 1st, 2014'.
 Note that this requires the file `as_GPS_utils.py`.

## 4.3 Public coroutines

### 4.3.1 Data validity

On startup after a cold start it may take time before valid data is received.
During and shortly after an outage messages will be absent. To avoid reading
stale data, reception of messages can be checked before accessing data.

 * `data_received` Boolean args: `position`, `course`, `date`,  `altitude`.
 All default `False`. The coroutine will pause until at least one valid message
 of each specified types has been received. This example will pause until new
 position and altitude messages have been received:

```python
while True:
    await my_gps.data_received(position=True, altitude=True)
    # Access these data values now
```

No option is provided for satellite data: this functionality is provided by the
`get_satellite_data` coroutine.

### 4.3.2 Satellite Data

Satellite data requires multiple sentences from the GPS and therefore requires
a coroutine which will pause execution until a complete set of data has been
acquired.

 * `get_satellite_data` No args. Waits for a set of GSV (satellites in view)
 sentences and returns a dictionary. Typical usage in a user coroutine:

```python
    d = await my_gps.get_satellite_data()
    print(d.keys())  # List of satellite PRNs
    print(d.values()) # [(elev, az, snr), (elev, az, snr)...]
```

Dictionary values are (elevation, azimuth, snr) where elevation and azimuth are
in degrees and snr (a measure of signal strength) is in dB in range 0-99.
Higher is better.

Note that if the GPS module does not support producing GSV sentences this
coroutine will pause forever. It can also pause for arbitrary periods if
satellite reception is blocked, such as in a building.

## 4.4 Public bound variables/properties

These are updated whenever a sentence of the relevant type has been correctly
received from the GPS unit. For crucial navigation data the `time_since_fix`
method may be used to determine how current these values are.

The sentence type which updates a value is shown in brackets e.g. (GGA).

### 4.4.1 Position/course

 * `course` Track angle in degrees. (VTG).
 * `altitude` Metres above mean sea level. (GGA).
 * `geoid_height` Height of geoid (mean sea level) in metres above WGS84
 ellipsoid. (GGA).
 * `magvar` Magnetic variation. Degrees. -ve == West. Current firmware does not
 produce this data: it will always read zero.

### 4.4.2 Statistics and status

The following are counts since instantiation.  
 * `crc_fails` Usually 0 but can occur on baudrate change.
 * `clean_sentences` Number of sentences received without major failures.
 * `parsed_sentences` Sentences successfully parsed.
 * `unsupported_sentences` This is incremented if a sentence is received which
 has a valid format and checksum, but is not supported by the class. This
 value will also increment if these are supported in a subclass. See
 [section 8](./GPS.md#8-developer-notes).

### 4.4.3 Date and time

 * `utc` (property) [hrs: int, mins: int, secs: int] UTC time e.g.
 [23, 3, 58]. Note the integer seconds value. The MTK3339 chip provides a float
 buts its value is always an integer. To achieve accurate subsecond timing see
 [section 6](./GPS.md#6-using-gps-for-accurate-timing).
 * `local_time` (property) [hrs: int, mins: int, secs: int] Local time.
 * `date` (property) [day: int, month: int, year: int] e.g. [23, 3, 18]
 * `local_offset` Local time offset in hrs as specified to constructor.
 * `epoch_time` Integer. Time in seconds since the epoch. Epoch start depends
 on whether running under MicroPython (Y2K) or Python 3.8+ (1970 on Unix).

The `utc`, `date` and `local_time` properties updates on receipt of RMC
messages. If a nonzero `local_offset` value is specified the `date` value will
update when local time passes midnight (local time and date are computed from
`epoch_time`).

### 4.4.4 Satellite data

 * `satellites_in_view` No. of satellites in view. (GSV).
 * `satellites_in_use` No. of satellites in use. (GGA).
 * `satellites_used` List of satellite PRN's. (GSA).
 * `pdop` Dilution of precision (GSA).
 * `hdop` Horizontal dilution of precsion (GSA).
 * `vdop` Vertical dilution of precision (GSA).

Dilution of Precision (DOP) values close to 1.0 indicate excellent quality
position data. Increasing values indicate decreasing precision.

## 4.5 Subclass hooks

The following public methods are null. They are intended for optional
overriding in subclasses. Or monkey patching if you like that sort of thing.

 * `reparse` Called after a supported sentence has been parsed.
 * `parse` Called when an unsupported sentence has been received.

If the received string is invalid (e.g. bad character or incorrect checksum)
these will not be called.

Both receive as arguments a list of strings, each being a segment of the comma
separated sentence. The '$' character in the first arg and the '*' character
and subsequent characters are stripped from the last. Thus if the string  
`b'$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n'`  
was received `reparse` would see  
`['GPGGA','123519','4807.038','N','01131.000','E','1','08','0.9','545.4','M','46.9','M','','']`

## 4.6 Public class variable

 * `FULL_CHECK` Default `True`. If set `False` disables CRC checking and other
 basic checks on received sentences. If GPS is linked directly to the target
 (rather than via long cables) these checks are arguably not neccessary.

###### [Top](./GPS.md#1-as_gps)

# 5. The GPS class read-write driver

This is a subclass of `AS_GPS` and supports all its public methods, coroutines
and bound variables. It provides support for sending PMTK command packets to
GPS modules based on the MTK3329/MTK3339 chip. These include:

 * Adafruit Ultimate GPS Breakout
 * Digilent PmodGPS
 * Sparkfun GPS Receiver LS20031
 * 43oh MTK3339 GPS Launchpad Boosterpack

A subset of the PMTK packet types is supported but this may be extended by
subclassing.

## 5.1 Test script

This assumes a Pyboard 1.x or Pyboard D with GPS on UART 4. To run issue:
```python
import as_drivers.as_gps.ast_pbrw
```

The test script will pause until a fix has been achieved. After that changes
are made for about 1 minute reporting data at the REPL and on the LEDs. On
completion (or `ctrl-c`) a factory reset is performed to restore the default
baudrate.  

LED's:
 * Red: Toggles each time a GPS update occurs.
 * Green: ON if GPS data is being received, OFF if no data received for >10s.
 * Yellow: Toggles each 4s if navigation updates are being received.

## 5.2 Usage example

This reduces to 2s the interval at which the GPS sends messages:

```python
import uasyncio as asyncio
from as_drivers.as_GPS.as_rwGPS import GPS
from machine import UART

uart = UART(4, 9600)
sreader = asyncio.StreamReader(uart)  # Create a StreamReader
swriter = asyncio.StreamWriter(uart, {})
gps = GPS(sreader, swriter)  # Instantiate GPS

async def test():
    print('waiting for GPS data')
    await gps.data_received(position=True, altitude=True)
    await gps.update_interval(2000)  # Reduce message rate
    for _ in range(10):
        print(gps.latitude(), gps.longitude(), gps.altitude)
        await asyncio.sleep(2)

asyncio.run(test())
```

## 5.3 GPS class Constructor

This takes two mandatory positional args:
 * `sreader` This is a `StreamReader` instance associated with the UART.
 * `swriter` This is a `StreamWriter` instance associated with the UART.

Optional positional args:
 * `local_offset` Local timezone offset in hours realtive to UTC (GMT).
 * `fix_cb` An optional callback which runs each time a valid fix is received.
 * `cb_mask` A bitmask determining which sentences will trigger the callback.
 Default `RMC`: the callback will occur on RMC messages only (see below).
 * `fix_cb_args` A tuple of args for the callback.
 * `msg_cb` Optional callback. This will run if any handled message is received
 and also for unhandled `PMTK` messages.
 * `msg_cb_args` A tuple of args for the above callback.

If implemented the message callback will receive the following positional args:
 1. The GPS instance.
 2. A list of text strings from the message.
 3. Any args provided in `msg_cb_args`.

In the case of handled messages the list of text strings has length 2. The
first is 'version', 'enabled' or 'antenna' followed by the value of the
relevant bound variable e.g. `['antenna', 3]`.

For unhandled messages text strings are as received, processed as per
[section 4.5](./GPS.md#45-subclass-hooks).

The args presented to the fix callback are as described in
[section 4.1](./GPS.md#41-constructor).

## 5.4 Public coroutines

 * `baudrate` Arg: baudrate. Must be 4800, 9600, 14400, 19200, 38400, 57600
 or 115200. See below.
 * `update_interval` Arg: interval in ms. Default 1000. Must be between 100
 and 10000. If the rate is to be increased see
 [notes on timing](GPS.md#9-notes-on-timing).
 * `enable` Determine the frequency with which each sentence type is sent. A
 value of 0 disables a sentence, a value of 1 causes it to be sent with each
 received position fix. A value of N causes it to be sent once every N fixes.  
 It takes 7 keyword-only integer args, one for each supported sentence. These,
 with default values, are:  
 `gll=0`, `rmc=1`, `vtg=1`, `gga=1`, `gsa=1`, `gsv=5`, `chan=0`. The last
 represents GPS channel status. These values are the factory defaults.
 * `command` Arg: a command from the following set:
   * `as_rwGPS.HOT_START` Use all available data in the chip's NV Store.
   * `as_rwGPS.WARM_START` Don't use Ephemeris at re-start.
   * `as_rwGPS.COLD_START` Don't use Time, Position, Almanacs and Ephemeris data
   at re-start.
   * `as_rwGPS.FULL_COLD_START` A 'cold_start', but additionally clear
   system/user configurations at re-start. That is, reset the receiver to the
   factory status.
   * `as_rwGPS.STANDBY` Put into standby mode. Sending any command resumes
   operation.
   * `as_rwGPS.DEFAULT_SENTENCES` Sets all sentence frequencies to factory
   default values as listed under `enable`.
   * `as_rwGPS.VERSION` Causes the GPS to report its firmware version. This will
   appear as the `version` bound variable when the report is received.
   * `as_rwGPS.ENABLE` Causes the GPS to report the enabled status of the various
   message types as set by the `enable` coroutine. This will appear as the
   `enable` bound variable when the report is received.
   * `as_rwGPS.ANTENNA` Causes the GPS to send antenna status messages. The
   status value will appear in the `antenna` bound variable each time a report is
   received.
   * `as_rwGPS.NO_ANTENNA` Turns off antenna messages.

**Antenna issues** In my testing the antenna functions have issues which
hopefully will be fixed in later firmware versions. The `NO_ANTENNA` message
has no effect. And, while issuing the `ANTENNA` message works, it affects the
response of the unit to subsequent commands. If possible issue it after all
other commands have been sent. I have also observed issues which can only be
cleared by power cycling the GPS.

### 5.4.1 Changing baudrate

I have experienced failures on a Pyboard V1.1 at baudrates higher than 19200.
This may be a problem with my GPS hardware (see below).

Further, there are problems (at least with my GPS firmware build) where setting
baudrates only works for certain rates. This is clearly an issue with the GPS
unit; rates of 19200, 38400, 57600 and 115200 work. Setting 4800 sets 115200.
Importantly 9600 does nothing. Hence the only way to restore the default is to
perform a `FULL_COLD_START`. The test programs do this. 

If you change the GPS baudrate the UART should be re-initialised immediately
after the `baudrate` coroutine terminates:

```python
async def change_status(gps, uart):
    await gps.baudrate(19200)
    uart.init(19200)
```

At risk of stating the obvious to seasoned programmers, say your application
changes the GPS unit's baudrate. If interrupted (with a bug or `ctrl-c`) the
GPS will still be running at the new baudrate. The application may need to be
designed to reflect this: see `ast_pbrw.py` which uses `try-finally` to reset
the baudrate in the event that the program terminates due to an exception or
otherwise.

Particular care needs to be used if a backup battery is employed as the GPS
will then remember its baudrate over a power cycle.

See also [notes on timing](./GPS.md#9-notes-on-timing).

## 5.5 Public bound variables

These are updated when a response to a command is received. The time taken for
this to occur depends on the GPS unit. One solution is to implement a message
callback. Alternatively await a coroutine which periodically (in intervals
measured in seconds) polls the value, returning it when it changes.

 * `version` Initially `None`. A list of version strings.
 * `enabled` Initially `None`. A dictionary of frequencies indexed by message
 type (see `enable` coroutine above).
 * `antenna` Initially 0. Values:  
 0 No report received.  
 1 Antenna fault.  
 2 Internal antenna.  
 3 External antenna.  

## 5.6 The parse method (developer note)

The null `parse` method in the base class is overridden. It intercepts the
single response to `VERSION` and `ENABLE` commands and updates the above bound
variables. The `ANTENNA` command causes repeated messages to be sent. These
update the `antenna` bound variable. These "handled" messages call the message
callback with the `GPS` instance followed by a list of sentence segments
followed by any args specified in the constructor.

Other `PMTK` messages are passed to the optional message callback as described
[in section 5.3](GPS.md#53-gps-class-constructor).

###### [Top](./GPS.md#1-as_gps)

# 6. Using GPS for accurate timing

Many GPS chips (e.g. MTK3339) provide a PPS signal which is a pulse occurring
at 1s intervals whose leading edge is a highly accurate UTC time reference.

This driver uses this pulse to provide accurate subsecond UTC and local time
values. The driver requires MicroPython because PPS needs a pin interrupt.

On STM platforms such as the Pyboard it may be used to set and to calibrate the
realtime clock (RTC). This functionality is not currently portable to other
chips.

See [Absolute accuracy](GPS.md#91-absolute-accuracy) for a discussion of
the absolute accuracy provided by this module (believed to be on the order of
+-70μs).

Two classes are provided: `GPS_Timer` for read-only access to the GPS device
and `GPS_RWTimer` for read/write access.

## 6.1 Test scripts

 * `as_GPS_time.py` Test scripts for read only driver.
 * `as_rwGPS_time.py` Test scripts for read/write driver.

On import, these will list available tests. Example usage:
```python
import as_drivers.as_GPS.as_GPS_time as test
test.usec()
```

## 6.2 Usage example

```python
import uasyncio as asyncio
import pyb
import as_drivers.as_GPS.as_tGPS as as_tGPS

async def test():
    fstr = '{}ms Time: {:02d}:{:02d}:{:02d}:{:06d}'
    red = pyb.LED(1)
    green = pyb.LED(2)
    uart = pyb.UART(4, 9600, read_buf_len=200)
    sreader = asyncio.StreamReader(uart)
    pps_pin = pyb.Pin('X3', pyb.Pin.IN)
    gps_tim = as_tGPS.GPS_Timer(sreader, pps_pin, local_offset=1,
                             fix_cb=lambda *_: red.toggle(),
                             pps_cb=lambda *_: green.toggle())
    print('Waiting for signal.')
    await gps_tim.ready()  # Wait for GPS to get a signal
    await gps_tim.set_rtc()  # Set RTC from GPS
    while True:
        await asyncio.sleep(1)
        # In a precision app, get the time list without allocation:
        t = gps_tim.get_t_split()
        print(fstr.format(gps_tim.get_ms(), t[0], t[1], t[2], t[3]))

asyncio.run(test())
```

## 6.3 GPS_Timer and GPS_RWTimer classes

These classes inherit from `AS_GPS` and `GPS` respectively, with read-only and
read/write access to the GPS hardware. All public methods and bound variables of
the base classes are supported. Additional functionality is detailed below.

### 6.3.1 GPS_Timer class Constructor

Mandatory positional args:
 * `sreader` The `StreamReader` instance associated with the UART.
 * `pps_pin` An initialised input `Pin` instance for the PPS signal.

Optional positional args:
 * `local_offset` See [base class](GPS.md#41-constructor) for details of
 these args.
 * `fix_cb`
 * `cb_mask`
 * `fix_cb_args`
 * `pps_cb` Callback runs when a PPS interrupt occurs. The callback runs in an
 interrupt context so it should return quickly and cannot allocate RAM. Default
 is a null method. See below for callback args.
 * `pps_cb_args` Default `()`. A tuple of args for the callback. The callback
 receives the `GPS_Timer` instance as the first arg, followed by any args in
 the tuple.

### 6.3.2 GPS_RWTimer class Constructor

This takes three mandatory positional args:
 * `sreader` The `StreamReader` instance associated with the UART.
 * `swriter` The `StreamWriter` instance associated with the UART.
 * `pps_pin` An initialised input `Pin` instance for the PPS signal.

Optional positional args:
 * `local_offset` See [base class](GPS.md#41-constructor) for
 details of these args.
 * `fix_cb`
 * `cb_mask`
 * `fix_cb_args`
 * `msg_cb`
 * `msg_cb_args`
 * `pps_cb` Callback runs when a PPS interrupt occurs. The callback runs in an
 interrupt context so it should return quickly and cannot allocate RAM. Default
 is a null method. See below for callback args.
 * `pps_cb_args` Default `()`. A tuple of args for the callback. The callback
 receives the `GPS_RWTimer` instance as the first arg, followed by any args in
 the tuple.

## 6.4 Public methods

The methods that return an accurate GPS time of day run as fast as possible. To
achieve this they avoid allocation and dispense with error checking: these
methods should not be called until a valid time/date message and PPS signal
have occurred. Await the `ready` coroutine prior to first use. Subsequent calls
may occur without restriction; see usage example above.

These methods use the MicroPython microsecond timer to interpolate between PPS
pulses. They do not involve the RTC. Hence they should work on any MicroPython
target supporting `machine.ticks_us`.

 * `get_ms` No args. Returns an integer: the period past midnight in ms.
 * `get_t_split` No args. Returns time of day in a list of form
 `[hrs: int, mins: int, secs: int, μs: int]`.
 * `close` No args. Shuts down the PPS pin interrupt handler. Usage is optional
 but in test situations avoids the ISR continuing to run after termination.

See [Absolute accuracy](GPS.md#91-absolute-accuracy) for a discussion of
the accuracy of these methods.

## 6.5 Public coroutines

All MicroPython targets:  
 * `ready` No args. Pauses until a valid time/date message and PPS signal have
 occurred.

STM hosts only:  
 * `set_rtc` No args. Sets the RTC to GPS time. Coroutine pauses for up
 to 1s as it waits for a PPS pulse.
 * `delta` No args. Returns no. of μs RTC leads GPS. Coro pauses for up to 1s.
 * `calibrate` Arg: integer, no. of minutes to run default 5. Calibrates the
 RTC and returns the calibration factor for it.

The `calibrate` coroutine sets the RTC (with any existing calibration removed)
and measures its drift with respect to the GPS time. This measurement becomes
more precise as time passes. It calculates a calibration value at 10s intervals
and prints progress information. When the calculated calibration factor is
repeatable within one digit (or the spcified time has elapsed) it terminates.
Typical run times are on the order of two miutes.

Achieving an accurate calibration factor takes time but does enable the Pyboard
RTC to achieve timepiece quality results. Note that calibration is lost on
power down: solutions are either to use an RTC backup battery or to store the
calibration factor in a file (or in code) and re-apply it on startup.

Crystal oscillator frequency has a small temperature dependence; consequently
the optimum calibration factor has a similar dependence. For best results allow
the hardware to reach working temperature before calibrating.

## 6.6 Absolute accuracy

The claimed absolute accuracy of the leading edge of the PPS signal is +-10ns.
In practice this is dwarfed by errors including latency in the MicroPython VM.
Nevertheless the `get_ms` method can be expected to provide 1 digit (+-1ms)
accuracy and the `get_t_split` method should provide accuracy on the order of
-5μs +65μs (standard deviation). This is based on a Pyboard running at 168MHz.
The reasoning behind this is discussed in
[section 9](./GPS.md#9-notes-on-timing).

## 6.7 Test/demo program as_GPS_time.py

Run by issuing
```python
import as_drivers.as_GPS.as_GPS_time as test
test.time()  # e.g.
```

This comprises the following test functions. Reset the chip with ctrl-d between
runs.
 * `time(minutes=1)` Print out GPS time values.
 * `calibrate(minutes=5)` Determine the calibration factor of the Pyboard RTC.
 Set it and calibrate it.
 * `drift(minutes=5)` Monitor the drift between RTC time and GPS time. At the
 end of the run, print the error in μs/hr and minutes/year.
 * `usec(minutes=1)` Measure the accuracy of `utime.ticks_us()` against the PPS
 signal. Print basic statistics at the end of the run. Provides an estimate of
 some limits to the absolute accuracy of the `get_t_split` method as discussed
 above.

# 7. Supported Sentences

 * GPRMC  GP indicates NMEA sentence (US GPS system).
 * GLRMC  GL indicates GLONASS (Russian system).
 * GNRMC  GN GNSS (Global Navigation Satellite System).
 * GPGLL
 * GLGLL
 * GPGGA
 * GLGGA
 * GNGGA
 * GPVTG
 * GLVTG
 * GNVTG
 * GPGSA
 * GLGSA
 * GPGSV
 * GLGSV

###### [Top](./GPS.md#1-as_gps)

# 8 Developer notes

These notes are for those wishing to adapt these drivers.

## 8.1 Subclassing

If support for further sentence types is required the `AS_GPS` class may be
subclassed. If a correctly formed sentence with a valid checksum is received,
but is not supported, the `parse` method is called. By default this is a
`lambda` which ignores args and returns `True`.

A subclass may override `parse` to parse such sentences. An example this may be
found in the `as_rwGPS.py` module.

The `parse` method receives an arg `segs` being a list of strings. These are
the parts of the sentence which were delimited by commas. See
[section 4.5](GPS.md#45-subclass-hooks) for details.

The `parse` method should return `True` if the sentence was successfully
parsed, otherwise `False`.

Where a sentence is successfully parsed by the driver, a null `reparse` method
is called. It receives the same string list as `parse`. It may be overridden in
a subclass, possibly to extract further information from the sentence.

## 8.2 Special test programs

These tests allow NMEA parsing to be verified in the absence of GPS hardware:  

 * `astests_pyb.py` Test with synthetic data on UART. GPS hardware replaced by
 a loopback on UART 4. Requires a Pyboard.
 * `astests.py` Test with synthetic data. Run on a PC under CPython 3.8+ or
 MicroPython. Run from the `v3` directory at the REPL as follows:

```python
from as_drivers.as_GPS.astests import run_tests
run_tests()
```
or at the command line:
```bash
$ micropython -m as_drivers.as_GPS.astests
```

###### [Top](./GPS.md#1-as_gps)

# 9. Notes on timing

At the default 1s update rate the GPS hardware emits a PPS pulse followed by a
set of messages. It then remains silent until the next PPS. At the default
baudrate of 9600 the UART continued receiving data for 400ms when a set of GPSV
messages came in. This time could be longer depending on data. So if an update
rate higher than the default 1 second is to be used, either the baudrate should
be increased or satellite information messages should be disabled.

The accuracy of the timing drivers may be degraded if a PPS pulse arrives while
the UART is still receiving. The update rate should be chosen to avoid this.

The PPS signal on the MTK3339 occurs only when a fix has been achieved. The
leading edge occurs on a 1s boundary with high absolute accuracy. It therefore
follows that the RMC message carrying the time/date of that second arrives
after the leading edge (because of processing and UART latency). It is also
the case that on a one-second boundary minutes, hours and the date may roll
over.

Further, the local_time offset can affect the date. These drivers aim to handle
these factors. They do this by storing the epoch time (as an integer number of
seconds) as the fundamental time reference. This is updated by the RMC message.
The `utc`, `date` and `localtime` properties convert this to usable values with
the latter two using the `local_offset` value to ensure correct results.

## 9.1 Absolute accuracy

Without an atomic clock synchronised to a Tier 1 NTP server, absolute accuracy
(Einstein notwithstanding :-)) is hard to prove. However if the manufacturer's
claim of the accuracy of the PPS signal is accepted, the errors contributed by
MicroPython can be estimated.

The driver interpolates between PPS pulses using `utime.ticks_us()` to provide
μs precision. The leading edge of PPS triggers an interrupt which records the
arrival time of PPS in the `acquired` bound variable. The ISR also records, to
1 second precision, an accurate datetime derived from the previous RMC message.
The time can therefore be estimated by taking the datetime and adding the
elapsed time since the time stored in the `acquired` bound variable. This is
subject to the following errors:

Sources of fixed lag:  
 * Latency in the function used to retrieve the time.
 * Mean value of the interrupt latency.

Sources of variable error:  
 * Variations in interrupt latency (small on Pyboard).
 * Inaccuracy in the `ticks_us` timer (significant over a 1 second interval).

With correct usage when the PPS interrupt occurs the UART will not be receiving
data (this can substantially affect ISR latency variability). Consequently, on
the Pyboard, variations in interrupt latency are small. Using an osciloscope a
normal latency of 15μs was measured with the `time` test in `as_GPS_time.py`
running. The maximum observed was 17μs.

The test program `as_GPS_time.py` has a test `usecs` which aims to assess the
sources of variable error. Over a period it repeatedly uses `ticks_us` to
measure the time between PPS pulses. Given that the actual time is effectively
constant the measurement is of error relative to the expected value of 1s. At
the end of the measurement period the test calculates some simple statistics on
the results. On targets other than a 168MHz Pyboard this may be run to estimate
overheads.

The timing method `get_t_split` measures the time when it is called, which it
records as quickly as possible. Assuming this has a similar latency to the ISR
there is likely to be a 30μs lag coupled with ~+-35μs (SD) jitter largely
caused by inaccuracy of `ticks_us` over a 1 second period. Note that I have
halved the jitter time on the basis that the timing method is called
asynchronously to PPS: the interval will centre on 0.5s. The assumption is that
inaccuracy in the `ticks_us` timer measured in μs is proportional to the
duration over which it is measured.

###### [Top](./GPS.md#1-as_gps)

# 10 Files

If space on the filesystem is limited, unneccessary files may be deleted. Many
applications will not need the read/write or timing files.

## 10.1 Basic files

 * `as_GPS.py` The library. Supports the `AS_GPS` class for read-only access to
 GPS hardware.
 * `as_GPS_utils.py` Additional formatted string methods for `AS_GPS`.
 * `ast_pb.py` Test/demo program: assumes a MicroPython hardware device with
 GPS connected to UART 4.
 * `log_kml.py` A simple demo which logs a route travelled to a .kml file which
 may be displayed on Google Earth.

On RAM-constrained devices `as_GPS_utils.py` may be omitted in which case the
`date_string` and `compass_direction` methods will be unavailable.

## 10.2 Files for read/write operation

 * `as_rwGPS.py` Supports the `GPS` class. This subclass of `AS_GPS` enables
 writing PMTK packets.
 * `as_rwGPS.py` Required if using the read/write variant.
 * `ast_pbrw.py` Test/demo script.

## 10.3 Files for timing applications
 
 * `as_tGPS.py` The library. Provides `GPS_Timer` and `GPS_RWTimer` classes.
 * `as_GPS_time.py` Test scripts for read only driver.
 * `as_rwGPS_time.py` Test scripts for read/write driver.

## 10.4 Special test programs

These tests allow NMEA parsing to be verified in the absence of GPS hardware:  

 * `astests.py` Test with synthetic data. Run on PC under CPython 3.8+ or MicroPython.
 * `astests_pyb.py` Test with synthetic data on UART. GPS hardware replaced by
 a loopback on UART 4. Requires a Pyboard.

# 11 References

[MicroPython]:https://micropython.org/
[frozen module]:https://learn.adafruit.com/micropython-basics-loading-modules/frozen-modules
[NMEA-0183]:http://aprs.gids.nl/nmea/
[TinyGPS]:http://arduiniana.org/libraries/tinygps/ 
[pyboard]:http://docs.micropython.org/en/latest/pyboard/pyboard/quickref.html
[MTK_command]:https://github.com/inmcm/MTK_commands
[Ultimate GPS Breakout]:http://www.adafruit.com/product/746
[micropyGPS]:https://github.com/inmcm/micropyGPS.git

###### [Top](./GPS.md#1-as_gps)
