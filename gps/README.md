# 1. as_GPS

This is an asynchronous device driver for GPS devices which communicate with
the driver via a UART. GPS NMEA sentence parsing is based on this excellent
library [micropyGPS].

The driver is designed to be extended by subclassing, for example to support
additional sentence types. It is compatible with Python 3.5 or later and also
with [MicroPython]. Testing was performed using a [pyboard] with the Adafruit
[Ultimate GPS Breakout] board.

Most GPS devices will work with the read-only driver as they emit NMEA
sentences on startup. An optional read-write driver is provided for
MTK3329/MTK3339 chips as used on the above board. This enables the device
configuration to be altered.

## 1.1 Overview

The `AS_GPS` object runs a coroutine which receives GPS NMEA sentences from the
UART and parses them as they arrive. Valid sentences cause local bound
variables to be updated. These can be accessed at any time with minimal latency
to access data such as position, altitude, course, speed, time and date.

## 1.2 Basic Usage

In the example below a UART is instantiated and an `AS_GPS` instance created.
A callback is specified which will run each time a valid fix is acquired.
The test runs for 60 seconds and therefore assumes that power has been applied
long enough for the GPS to have started to acquire data.

```python
import uasyncio as asyncio
import as_GPS
from machine import UART
def callback(gps, *_):  # Runs for each valid fix
    print(gps.latitude(), gps.longitude(), gps.altitude)

uart = UART(4, 9600)
sreader = asyncio.StreamReader(uart)  # Create a StreamReader
my_gps = as_GPS.AS_GPS(sreader, fix_cb=callback)  # Instantiate GPS

async def test():
    await asyncio.sleep(60)  # Run for one minute
loop = asyncio.get_event_loop()
loop.run_until_complete(test())
```

## 1.3 Files

The following are relevant to the default read-only driver.

 * `as_GPS.py` The library. Supports the `AS_GPS` class for read-only access to
 GPS hardware.
 * `ast_pb.py` Test/demo program: assumes a MicroPython hardware device with
 GPS connected to UART 4.
 * `log_kml.py` A simple demo which logs a route travelled to a .kml file which
 may be displayed on Google Earth.
 * `astests.py` Test with synthetic data. Run on CPython 3.x or MicroPython.
 * `astests_pyb.py` Test with synthetic data on UART. GPS hardware replaced by
 a loopback on UART 4. Requires CPython 3.5 or later or MicroPython and
 `uasyncio`.

Additional files relevant to the read/write driver are listed
[here](./README.md#31-files).

## 1.4 Installation

### 1.4.1 Micropython

To install on "bare metal" hardware such as the Pyboard copy the file
`as_GPS.py` onto the device's filesystem and ensure that `uasyncio` is
installed. The code has been tested on the Pyboard with `uasyncio` V2 and the
Adafruit [Ultimate GPS Breakout] module. If memory errors are encountered on
resource constrained devices install as a [frozen module].

For the [read/write driver](./README.md#3-the-gps-class-read/write-driver) the
file `as_rwGPS.py` must also be installed.

### 1.4.2 Python 3.5 or later

On platforms with an underlying OS such as the Raspberry Pi ensure that
`as_GPS.py` (and optionally `as_rwGPS.py`) is on the Python path and that the
Python version is 3.5 or later.

# 2. The AS_GPS Class read-only driver

Method calls and access to bound variables are nonblocking and return the most
current data. This is updated transparently by a coroutine. In situations where
updates cannot be achieved, for example in buildings or tunnels, values will be
out of date. Whether this matters and any action to take is application
dependent.

Three mechanisms exist for responding to outages.  
 * Check the `time_since_fix` method [section 2.2.3](./README.md#223-time-and-date).
 * Pass a `fix_cb` callback to the constructor (see below).
 * Cause a coroutine to pause until an update is received: see
 [section 3.2](./README.md#231-data-validity). This ensures current data.

## 2.1 Constructor

Mandatory positional arg:
 * `sreader` This is a `StreamReader` instance associated with the UART.
Optional positional args:
 * `local_offset` Local timezone offset in hours realtive to UTC (GMT).
 * `fix_cb` An optional callback. This runs after a valid message of a chosen
 type has been received and processed.
 * `cb_mask` A bitmask determining which sentences will trigger the callback.
 Default `RMC`: the callback will occur on RMC messages only (see below).
 * `fix_cb_args` A tuple of args for the callback (default `()`).

Notes:  
`local_offset` does not affect the date value.  
If `sreader` is `None` a special test mode is engaged (see `astests.py`).

### 2.1.1 The fix callback

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

## 2.2 Public Methods

### 2.2.1 Location

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

### 2.2.2 Course

 * `speed` Optional arg `unit=KPH`. Returns the current speed in the specified
 units. Options: `as_GPS.KPH`, `as_GPS.MPH`, `as_GPS.KNOT`.

 * `speed_string` Optional arg `unit=as_GPS.KPH`. Returns the current speed in
 the specified units. Options `as_GPS.KPH`, `as_GPS.MPH`, `as_GPS.KNOT`.

 * `compass_direction` No args. Returns current course as a string e.g. 'ESE'
 or 'NW'

### 2.2.3 Time and date

 * `time_since_fix` No args. Returns time in milliseconds since last valid fix.

 * `date_string` Optional arg `formatting=MDY`. Returns the date as
 a string. Formatting options:  
 `as_GPS.MDY` returns 'MM/DD/YY'.  
 `as_GPS.DMY` returns 'DD/MM/YY'.  
 `as_GPS.LONG` returns a string of form 'January 1st, 2014'.

 * `time` No args. Returns the current time in form 'hh:mm:ss.sss'.

## 2.3 Public coroutines

### 2.3.1 Data validity

On startup after a cold start it may take time before valid data is received.
During and shortly after an outage messages will be absent. To avoid reading
stale data reception of messages can be checked before accessing data.

 * `data_received` Boolean args: `position`, `course`, `date`,  `altitude`.
 All default `False`. The coroutine will pause until valid messages of the
 specified types have been received. For example:

```python
while True:
    await my_gps.data_received(position=True, altitude=True)
    # can now access these data values with confidence
```

No check is provided for satellite data as this is checked by the
`get_satellite_data` coroutine.

### 2.3.2 Satellite Data

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

## 2.4 Public bound variables

These are updated whenever a sentence of the relevant type has been correctly
received from the GPS unit. For crucial navigation data the `time_since_fix`
method may be used to determine how current these values are.

The sentence type which updates a value is shown in brackets e.g. (GGA).

### 2.4.1 Position/course

 * `course` Track angle in degrees. (VTG).
 * `altitude` Metres above mean sea level. (GGA).
 * `geoid_height` Height of geoid (mean sea level) in metres above WGS84
 ellipsoid. (GGA).
 * `magvar` Magnetic variation. Degrees. -ve == West. Current firmware does not
 produce this data and it will always read zero.

### 2.4.2 Statistics and status

The following are counts since instantiation.  
 * `crc_fails` Usually 0 but can occur on baudrate change.
 * `clean_sentences` Number of sentences received without major failures.
 * `parsed_sentences` Sentences successfully parsed.
 * `unsupported_sentences` This is incremented if a sentence is received with a
 valid format and checksum, but is not supported by the class. This value will
 also increment if these are supported in a subclass (see section 5).

### 2.4.3 Date and time

As received from most recent GPS message.

 * `timestamp` [hrs, mins, secs] e.g. [12, 15, 3.23]
 * `date` [day, month, year] e.g. [23, 3, 18]
 * `local_offset` Local time offset in hrs as specified to constructor.

### 2.4.4 Satellite data

 * `satellites_in_view` No. of satellites in view. (GSV).
 * `satellites_in_use` No. of satellites in use. (GGA).
 * `satellites_used` List of satellite PRN's. (GSA).
 * `pdop` Dilution of precision (GSA).
 * `hdop` Horizontal dilution of precsion (GSA).
 * `vdop` Vertical dilution of precision (GSA).

Dilution of Precision (DOP) values close to 1.0 indicate excellent quality
position data. Increasing values indicate decreasing precision.

## 2.5 Subclass hooks

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

# 3. The GPS class read/write driver

This is a subclass of `AS_GPS` and supports all its public methods, coroutines
and bound variables. It provides limited support for sending PMTK command
packets to GPS modules based on the MTK3329/MTK3339 chip. These include:

 * Adafruit Ultimate GPS Breakout
 * Digilent PmodGPS
 * Sparkfun GPS Receiver LS20031
 * 43oh MTK3339 GPS Launchpad Boosterpack

## 3.1 Files

 * `as_rwGPS.py` Supports the `GPS` class. This subclass of `AS_GPS` enables
 writing a limited subset of the MTK commands used on many popular devices.

## 3.2 Constructor

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
relevant bound variable e.g. ['antenna', 3].

For unhandled messages text strings are as received, except that element 0 has
the '$' symbol removed. The last element is the last informational string - the
checksum has been verified and is not in the list.

The args presented to the fix callback are as described in
[section 2.1](./README.md#21-constructor).

## 3.3 Public coroutines

 * `baudrate` Arg: baudrate. Must be 4800, 9600, 14400, 19200, 38400, 57600 or
 115200. See below.
 * `update_interval` Arg: interval in ms. Default 1000. Must be between 100 and
 10000.
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

### 3.3.1 Changing baudrate

The if you change the GPS baudrate the UART should be re-initialised
immediately after the `baudrate` coroutine terminates:

```python
async def change_status(gps, uart):
    await gps.baudrate(19200)
    uart.init(19200)
```

At risk of stating the obvious to seasoned programmers, if your application
changes the GPS unit's baudrate and you interrupt it with ctrl-c, the GPS will
still be running at the new baudrate. Your application may need to be designed
to reflect this: see `ast_pbrw.py` which uses try-finally to reset the baudrate
in the event that the program terminates due to an exception or otherwise.

Particular care needs to be used if a backup battery is employed as the GPS
will then remember its baudrate over a power cycle.

## 3.4 Public bound variables

These are updated when a response to a command is received. The time taken for
this to occur depends on the GPS unit. One solution is to implement a message
callback. Alternatively await a coroutine which periodically (in intervals
measured in seconds) polls the value, returning it when it changes.

 * `version` Initially `None`. A list of version strings.
 * `enabled` Initially `None`. A dictionary of frequencies indexed by message
 type.
 * `antenna` Initially 0. Values:
 0 No report received.  
 1 Antenna fault.  
 2 Internal antenna.  
 3 External antenna.  

## 3.5 The parse method

The default `parse` method is redefined. It intercepts the single response to
`VERSION` and `ENABLE` commands and updates the above bound variables. The
`ANTENNA` command causes repeated messages to be sent. These update the
`antenna` bound variable. These "handled" messages call the message callback
with

Other `PMTK` messages are passed to the optional message callback as described
[in section 3.2](./README.md#32-constructor).

# 4. Supported Sentences

 * GPRMC  GP indicates NMEA sentence
 * GLRMC  GL indicates GLONASS (Russian system)
 * GNRMC  GN GNSS (Global Navigation Satellite System)
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

# 5. Subclassing

If support for further sentence types is required the `AS_GPS` class may be
subclassed. If a correctly formed sentence with a valid checksum is received,
but is not supported, the `parse` method is called. By default this is a
`lambda` which ignores args and returns `True`.

An example of this may be found in the `as_rwGPS.py` module.

A subclass may redefine this to attempt to parse such sentences. The method
receives an arg `segs` being a list of strings. These are the parts of the
sentence which were delimited by commas. `segs[0]` is the sentence type with
the leading '$' character removed.

It should return `True` if the sentence was successfully parsed, otherwise
`False`.

[MicroPython]:https://micropython.org/
[frozen module]:https://learn.adafruit.com/micropython-basics-loading-modules/frozen-modules
[NMEA-0183]:http://aprs.gids.nl/nmea/
[TinyGPS]:http://arduiniana.org/libraries/tinygps/ 
[pyboard]:http://docs.micropython.org/en/latest/pyboard/pyboard/quickref.html
[MTK_command]:https://github.com/inmcm/MTK_commands
[Ultimate GPS Breakout]:http://www.adafruit.com/product/746
[micropyGPS]:https://github.com/inmcm/micropyGPS.git