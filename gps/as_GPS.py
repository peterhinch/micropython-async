# as_GPS.py Asynchronous device driver for GPS devices using a UART.
# Sentence parsing based on MicropyGPS by Michael Calvin McCoy
# https://github.com/inmcm/micropyGPS
# http://www.gpsinformation.org/dale/nmea.htm
# Docstrings removed because of question marks over their use in resource
# constrained systems e.g. https://github.com/micropython/micropython/pull/3748

# Copyright (c) 2018 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# astests.py runs under CPython but not MicroPython because mktime is missing
# from Unix build of utime

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    from micropython import const
except ImportError:
    const = lambda x : x

from math import modf

# Angle formats
DD = const(1)
DMS = const(2)
DM = const(3)
KML = const(4)
# Speed units
KPH = const(10)
MPH = const(11)
KNOT = const(12)
# Date formats
MDY = const(20)
DMY = const(21)
LONG = const(22)

# Sentence types
RMC = const(1)
GLL = const(2)
VTG = const(4)
GGA = const(8)
GSA = const(16)
GSV = const(32)
# Messages carrying data
POSITION = const(RMC | GLL | GGA)
ALTITUDE = const(GGA)
DATE = const(RMC)
COURSE = const(RMC | VTG)


class AS_GPS(object):
    # Can omit time consuming checks: CRC 6ms Bad char and line length 9ms
    FULL_CHECK = True
    _SENTENCE_LIMIT = 76  # Max sentence length (based on GGA sentence)
    _NO_FIX = 1

    # Return day of week from date. Pyboard RTC format: 1-7 for Monday through Sunday.
    # https://stackoverflow.com/questions/9847213/how-do-i-get-the-day-of-week-given-a-date-in-python?noredirect=1&lq=1
    # Adapted for Python 3 and Pyboard RTC format.
    @staticmethod
    def _week_day(year, month, day, offset = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]):
        aux = year - 1700 - (1 if month <= 2 else 0)
        # day_of_week for 1700/1/1 = 5, Friday
        day_of_week  = 5
        # partial sum of days betweem current date and 1700/1/1
        day_of_week += (aux + (1 if month <= 2 else 0)) * 365
        # leap year correction
        day_of_week += aux // 4 - aux // 100 + (aux + 100) // 400
        # sum monthly and day offsets
        day_of_week += offset[month - 1] + (day - 1)
        day_of_week %= 7
        day_of_week = day_of_week if day_of_week else 7
        return day_of_week

    # 8-bit xor of characters between "$" and "*". Takes 6ms on Pyboard!
    @staticmethod
    def _crc_check(res, ascii_crc):
        try:
            crc = int(ascii_crc, 16)
        except ValueError:
            return False
        x = 1
        crc_xor = 0
        while res[x] != '*':
            crc_xor ^= ord(res[x])
            x += 1
        return crc_xor == crc

    def __init__(self, sreader, local_offset=0, fix_cb=lambda *_ : None, cb_mask=RMC, fix_cb_args=()):
        self._sreader = sreader  # If None testing: update is called with simulated data
        self._fix_cb = fix_cb
        self.cb_mask = cb_mask
        self._fix_cb_args = fix_cb_args
        self.battery = False  # Assume no backup battery

        # CPython compatibility. Import utime or time for fix time handling.
        try:
            import utime
            self._get_time = utime.ticks_ms
            self._time_diff = utime.ticks_diff
            self._localtime = utime.localtime
            self._mktime = utime.mktime
        except ImportError:
            # Otherwise default to time module for non-embedded implementations
            # Should still support millisecond resolution.
            import time
            self._get_time = time.time
            self._time_diff = lambda start, end: 1000 * (start - end)
            self._localtime = time.localtime
            self._mktime = time.mktime

        # Key: currently supported NMEA sentences. Value: parse method.
        self.supported_sentences = {'GPRMC': self._gprmc, 'GLRMC': self._gprmc,
                                    'GPGGA': self._gpgga, 'GLGGA': self._gpgga,
                                    'GPVTG': self._gpvtg, 'GLVTG': self._gpvtg,
                                    'GPGSA': self._gpgsa, 'GLGSA': self._gpgsa,
                                    'GPGSV': self._gpgsv, 'GLGSV': self._gpgsv,
                                    'GPGLL': self._gpgll, 'GLGLL': self._gpgll,
                                    'GNGGA': self._gpgga, 'GNRMC': self._gprmc,
                                    'GNVTG': self._gpvtg,
                                    }

        #####################
        # Object Status Flags
        self._fix_time = None

        #####################
        # Sentence Statistics
        self.crc_fails = 0
        self.clean_sentences = 0
        self.parsed_sentences = 0
        self.unsupported_sentences = 0

        #####################
        # Data From Sentences
        # Time. http://www.gpsinformation.org/dale/nmea.htm indicates seconds
        # is an integer. However hardware returns a float, but the fractional
        # part is always zero. So treat seconds value as an integer. For
        # precise timing use PPS signal and as_tGPS library.
        self.local_offset = local_offset  # hrs
        self.epoch_time = 0  # Integer secs since epoch (Y2K under MicroPython)
        # Add ms if supplied by device. Only used by timing drivers.
        self.msecs = 0

        # Position/Motion
        self._latitude = [0, 0.0, 'N']  # (°, mins, N/S)
        self._longitude = [0, 0.0, 'W']  # (°, mins, E/W)
        self._speed = 0.0  # Knot
        self.course = 0.0  # ° clockwise from N
        self.altitude = 0.0  # Metres
        self.geoid_height = 0.0  # Metres
        self.magvar = 0.0  # Magnetic variation (°, -ve == west)

        # State variables
        self._last_sv_sentence = 0  # for GSV parsing
        self._total_sv_sentences = 0
        self._satellite_data = dict()  # for get_satellite_data()
        self._update_ms = 1000  # Update rate for timing drivers. Default 1 sec.

        # GPS Info
        self.satellites_in_view = 0
        self.satellites_in_use = 0
        self.satellites_used = []
        self.hdop = 0.0
        self.pdop = 0.0
        self.vdop = 0.0

        # Received status
        self._valid = 0  # Bitfield of received sentences
        if sreader is not None:  # Running with UART data
            loop = asyncio.get_event_loop()
            loop.create_task(self._run(loop))

    ##########################################
    # Data Stream Handler Functions
    ##########################################

    async def _run(self, loop):
        while True:
            res = await self._sreader.readline()
            try:
                res = res.decode('utf8')
            except UnicodeError:  # Garbage: can happen e.g. on baudrate change
                continue
            loop.create_task(self._update(res))
            await asyncio.sleep(0)  # Ensure task runs and res is copied

    # Update takes a line of text
    async def _update(self, line):
        line = line.rstrip()  # Copy line
        if self.FULL_CHECK:  # 9ms on Pyboard
            try:
                next(c for c in line if ord(c) < 10 or ord(c) > 126)
                return  # Bad character received
            except StopIteration:
                pass  # All good
            await asyncio.sleep(0)
            if len(line) > self._SENTENCE_LIMIT or not '*' in line:
                return  # Too long or malformed

        a = line.split(',')
        segs = a[:-1] + a[-1].split('*')
        await asyncio.sleep(0)

        if self.FULL_CHECK:  # 6ms on Pyboard
            if not self._crc_check(line, segs[-1]):
                self.crc_fails += 1  # Update statistics
                return
            await asyncio.sleep(0)

        self.clean_sentences += 1  # Sentence is good but unparsed.
        segs[0] = segs[0][1:]  # discard $
        segs = segs[:-1]  # and checksum
        if segs[0] in self.supported_sentences:
            try:
                s_type = self.supported_sentences[segs[0]](segs)  # Parse
            except ValueError:
                s_type = False
            await asyncio.sleep(0)
            if isinstance(s_type, int) and (s_type & self.cb_mask):
                # Successfully parsed, data was valid and mask matches sentence type
                self._fix_cb(self, s_type, *self._fix_cb_args)  # Run the callback
            if s_type:  # Successfully parsed
                if self.reparse(segs):  # Subclass hook
                    self.parsed_sentences += 1
                    return segs[0]  # For test programs
        else:
            if self.parse(segs):  # Subclass hook
                self.parsed_sentences += 1
                self.unsupported_sentences += 1
                return segs[0]  # For test programs

    # Optional hooks for subclass
    def parse(self, segs):  # Parse unsupported sentences
        return True

    def reparse(self, segs):  # Re-parse supported sentences
        return True

    ########################################
    # Fix and Time Functions
    ########################################

    # Caller traps ValueError
    def _fix(self, gps_segments, idx_lat, idx_long):
        # Latitude
        l_string = gps_segments[idx_lat]
        lat_degs = int(l_string[0:2])
        lat_mins = float(l_string[2:])
        lat_hemi = gps_segments[idx_lat + 1]
        # Longitude
        l_string = gps_segments[idx_long]
        lon_degs = int(l_string[0:3])
        lon_mins = float(l_string[3:])
        lon_hemi = gps_segments[idx_long + 1]

        if lat_hemi not in 'NS'or lon_hemi not in 'EW':
            raise ValueError
        self._latitude[0] = lat_degs  # In-place to avoid allocation
        self._latitude[1] = lat_mins
        self._latitude[2] = lat_hemi
        self._longitude[0] = lon_degs
        self._longitude[1] = lon_mins
        self._longitude[2] = lon_hemi
        self._fix_time = self._get_time()

    def _dtset(self, _):  # For subclass
        pass

    # A local offset may exist so check for date rollover. Local offsets can
    # include fractions of an hour but not seconds (AFAIK).
    # Caller traps ValueError
    def _set_date_time(self, utc_string, date_string):
        if not date_string or not utc_string:
            raise ValueError
        hrs = int(utc_string[0:2])  # h
        mins = int(utc_string[2:4])  # mins
        # Secs from MTK3339 chip is a float but others may return only 2 chars
        # for integer secs. If a float keep epoch as integer seconds and store
        # the fractional part as integer ms (ms since midnight fits 32 bits).
        fss, fsecs = modf(float(utc_string[4:]))
        secs = int(fsecs)
        self.msecs = int(fss * 1000)
        d = int(date_string[0:2])  # day
        m = int(date_string[2:4])  # month
        y = int(date_string[4:6]) + 2000  # year
        wday = self._week_day(y, m, d)
        t = int(self._mktime((y, m, d, hrs, mins, int(secs), wday - 1, 0, 0)))
        self.epoch_time = t  # This is the fundamental datetime reference.
        self._dtset(wday)  # Subclass may override

    ########################################
    # Sentence Parsers
    ########################################

# For all parsers:
# Initially the ._valid bit for the sentence type is cleared.
# On error a ValueError is raised: trapped by the caller.
# On successful parsing the ._valid bit is set.
# The ._valid mechanism enables the data_received coro to determine what
# sentence types have been received.

    # Chip sends rubbish RMC messages before first PPS pulse, but these have
    # data valid set to 'V' (void)
    def _gprmc(self, gps_segments):  # Parse RMC sentence
        self._valid &= ~RMC
        # Check Receiver Data Valid Flag ('A' active)
        if not self.battery:
            if gps_segments[2] != 'A':
                raise ValueError

        # UTC Timestamp and date. Can raise ValueError.
        self._set_date_time(gps_segments[1], gps_segments[9])
        # Check Receiver Data Valid Flag ('A' active)
        if gps_segments[2] != 'A':
            raise ValueError

        # Data from Receiver is Valid/Has Fix. Longitude / Latitude
        # Can raise ValueError.
        self._fix(gps_segments, 3, 5)
        # Speed
        spd_knt = float(gps_segments[7])
        # Course
        course = float(gps_segments[8])
        # Add Magnetic Variation if firmware supplies it
        if gps_segments[10]:
            mv = float(gps_segments[10])
            if gps_segments[11] not in ('EW'):
                raise ValueError
            self.magvar = mv if gps_segments[11] == 'E' else -mv
        # Update Object Data
        self._speed = spd_knt
        self.course = course
        self._valid |= RMC
        return RMC

    def _gpgll(self, gps_segments):  # Parse GLL sentence
        self._valid &= ~GLL
        # Check Receiver Data Valid Flag
        if gps_segments[6] != 'A':  # Invalid. Don't update data
            raise ValueError

        # Data from Receiver is Valid/Has Fix. Longitude / Latitude
        self._fix(gps_segments, 1, 3)
        # Update Last Fix Time
        self._valid |= GLL
        return GLL

    # Chip sends VTG messages with meaningless data before getting a fix.
    def _gpvtg(self, gps_segments):  # Parse VTG sentence
        self._valid &= ~VTG
        course = float(gps_segments[1])
        spd_knt = float(gps_segments[5])
        self._speed = spd_knt
        self.course = course
        self._valid |= VTG
        return VTG

    def _gpgga(self, gps_segments):  # Parse GGA sentence
        self._valid &= ~GGA
        # Number of Satellites in Use
        satellites_in_use = int(gps_segments[7])
        # Horizontal Dilution of Precision
        hdop = float(gps_segments[8])
        # Get Fix Status
        fix_stat = int(gps_segments[6])

        # Process Location and Altitude if Fix is GOOD
        if fix_stat:
            # Longitude / Latitude
            self._fix(gps_segments, 2, 4)
            # Altitude / Height Above Geoid
            altitude = float(gps_segments[9])
            geoid_height = float(gps_segments[11])
            # Update Object Data
            self.altitude = altitude
            self.geoid_height = geoid_height
            self._valid |= GGA

        # Update Object Data
        self.satellites_in_use = satellites_in_use
        self.hdop = hdop
        return GGA

    def _gpgsa(self, gps_segments):  # Parse GSA sentence
        self._valid &= ~GSA
        # Fix Type (None,2D or 3D)
        fix_type = int(gps_segments[2])
        # Read All (up to 12) Available PRN Satellite Numbers
        sats_used = []
        for sats in range(12):
            sat_number_str = gps_segments[3 + sats]
            if sat_number_str:
                sat_number = int(sat_number_str)
                sats_used.append(sat_number)
            else:
                break
        # PDOP,HDOP,VDOP
        pdop = float(gps_segments[15])
        hdop = float(gps_segments[16])
        vdop = float(gps_segments[17])

        # If Fix is GOOD, update fix timestamp
        if fix_type <= self._NO_FIX:  # Deviation from Michael McCoy's logic. Is this right?
            raise ValueError
        self.satellites_used = sats_used
        self.hdop = hdop
        self.vdop = vdop
        self.pdop = pdop
        self._valid |= GSA
        return GSA

    def _gpgsv(self, gps_segments):
        # Parse Satellites in View (GSV) sentence. Updates no. of SV sentences,
        # the no. of the last SV sentence parsed, and data on each satellite
        # present in the sentence.
        self._valid &= ~GSV
        num_sv_sentences = int(gps_segments[1])
        current_sv_sentence = int(gps_segments[2])
        sats_in_view = int(gps_segments[3])

        # Create a blank dict to store all the satellite data from this sentence in:
        # satellite PRN is key, tuple containing telemetry is value
        satellite_dict = dict()

        # Calculate  Number of Satelites to pull data for and thus how many segment positions to read
        if num_sv_sentences == current_sv_sentence:
            sat_segment_limit = ((sats_in_view % 4) * 4) + 4  # Last sentence may have 1-4 satellites
        else:
            sat_segment_limit = 20  # Non-last sentences have 4 satellites and thus read up to position 20

        # Try to recover data for up to 4 satellites in sentence
        for sats in range(4, sat_segment_limit, 4):

            # If a PRN is present, grab satellite data
            if gps_segments[sats]:
                try:
                    sat_id = int(gps_segments[sats])
                except IndexError:
                    raise ValueError  # Abandon

                try:  # elevation can be null (no value) when not tracking
                    elevation = int(gps_segments[sats+1])
                except (ValueError,IndexError):
                    elevation = None

                try:  # azimuth can be null (no value) when not tracking
                    azimuth = int(gps_segments[sats+2])
                except (ValueError,IndexError):
                    azimuth = None

                try:  # SNR can be null (no value) when not tracking
                    snr = int(gps_segments[sats+3])
                except (ValueError,IndexError):
                    snr = None
            # If no PRN is found, then the sentence has no more satellites to read
            else:
                break

            # Add Satellite Data to Sentence Dict
            satellite_dict[sat_id] = (elevation, azimuth, snr)

        # Update Object Data
        self._total_sv_sentences = num_sv_sentences
        self._last_sv_sentence = current_sv_sentence
        self.satellites_in_view = sats_in_view

        # For a new set of sentences, we either clear out the existing sat data or
        # update it as additional SV sentences are parsed
        if current_sv_sentence == 1:
            self._satellite_data = satellite_dict
        else:
            self._satellite_data.update(satellite_dict)
        # Flag that a msg has been received. Does not mean a full set of data is ready.
        self._valid |= GSV
        return GSV

    #########################################
    # User Interface Methods
    #########################################

    # Data Validity. On startup data may be invalid. During an outage it will be absent.
    async def data_received(self, position=False, course=False, date=False,
                            altitude=False):
        self._valid = 0  # Assume no messages at start
        result = False
        while not result:
            result = True
            await asyncio.sleep(1)  # Successfully parsed messages set ._valid bits
            if position and not self._valid & POSITION:
                result = False
            if date and not self._valid & DATE:
                result = False
            # After a hard reset the chip sends course messages even though no fix
            # was received. Ignore this garbage until a fix is received.
            if course:
                if self._valid & COURSE:
                    if not self._valid & POSITION:
                        result = False
                else:
                    result = False
            if altitude and not self._valid & ALTITUDE:
                result = False

    def latitude(self, coord_format=DD):
        # Format Latitude Data Correctly
        if coord_format == DD:
            decimal_degrees = self._latitude[0] + (self._latitude[1] / 60)
            return [decimal_degrees, self._latitude[2]]
        elif coord_format == DMS:
            mins = int(self._latitude[1])
            seconds = round((self._latitude[1] - mins) * 60)
            return [self._latitude[0], mins, seconds, self._latitude[2]]
        elif coord_format == DM:
            return self._latitude
        raise ValueError('Unknown latitude format.')

    def longitude(self, coord_format=DD):
        # Format Longitude Data Correctly
        if coord_format == DD:
            decimal_degrees = self._longitude[0] + (self._longitude[1] / 60)
            return [decimal_degrees, self._longitude[2]]
        elif coord_format == DMS:
            mins = int(self._longitude[1])
            seconds = round((self._longitude[1] - mins) * 60)
            return [self._longitude[0], mins, seconds, self._longitude[2]]
        elif coord_format == DM:
            return self._longitude
        raise ValueError('Unknown longitude format.')

    def speed(self, units=KNOT):
        if units == KNOT:
            return self._speed
        if units == KPH:
            return self._speed * 1.852
        if units == MPH:
            return self._speed * 1.151
        raise ValueError('Unknown speed units.')

    async def get_satellite_data(self):
        self._total_sv_sentences = 0
        while self._total_sv_sentences == 0:
            await asyncio.sleep(0)
        while self._total_sv_sentences > self._last_sv_sentence:
            await asyncio.sleep(0)
        return self._satellite_data

    def time_since_fix(self):  # ms since last valid fix
        if self._fix_time is None:
            return -1  # No fix yet found
        return self._time_diff(self._get_time(), self._fix_time)

    def compass_direction(self):  # Return cardinal point as string.
        from as_GPS_utils import compass_direction
        return compass_direction(self)

    def latitude_string(self, coord_format=DM):
        if coord_format == DD:
            return '{:3.6f}° {:s}'.format(*self.latitude(DD))
        if coord_format == DMS:
            return """{:3d}° {:2d}' {:2d}" {:s}""".format(*self.latitude(DMS))
        if coord_format == KML:
            form_lat = self.latitude(DD)
            return '{:4.6f}'.format(form_lat[0] if form_lat[1] == 'N' else -form_lat[0])
        return "{:3d}° {:3.4f}' {:s}".format(*self.latitude(coord_format))

    def longitude_string(self, coord_format=DM):
        if coord_format == DD:
            return '{:3.6f}° {:s}'.format(*self.longitude(DD))
        if coord_format == DMS:
            return """{:3d}° {:2d}' {:2d}" {:s}""".format(*self.longitude(DMS))
        if coord_format == KML:
            form_long = self.longitude(DD)
            return '{:4.6f}'.format(form_long[0] if form_long[1] == 'E' else -form_long[0])
        return "{:3d}° {:3.4f}' {:s}".format(*self.longitude(coord_format))

    def speed_string(self, unit=KPH):
        sform = '{:3.2f} {:s}'
        speed = self.speed(unit)
        if unit == MPH:
            return sform.format(speed, 'mph')
        elif unit == KNOT:
            return sform.format(speed, 'knots')
        return sform.format(speed, 'km/h')

    # Return local time (hrs: int, mins: int, secs:float)
    @property
    def local_time(self):
        t = self.epoch_time + int(3600 * self.local_offset)
        _, _, _, hrs, mins, secs, *_ = self._localtime(t)
        return hrs, mins, secs

    @property
    def date(self):
        t = self.epoch_time + int(3600 * self.local_offset)
        y, m, d, *_ = self._localtime(t)
        return d, m, y - 2000

    @property
    def utc(self):
        t = self.epoch_time
        _, _, _, hrs, mins, secs, *_ = self._localtime(t)
        return hrs, mins, secs

    def time_string(self, local=True):
        hrs, mins, secs = self.local_time if local else self.utc
        return '{:02d}:{:02d}:{:02d}'.format(hrs, mins, secs)

    def date_string(self, formatting=MDY):
        from as_GPS_utils import date_string
        return date_string(self, formatting)
