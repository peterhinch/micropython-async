"""
# MicropyGPS - a GPS NMEA sentence parser for Micropython/Python 3.X
# Copyright (c) 2017 Michael Calvin McCoy (calvin.mccoy@gmail.com)
# The MIT License (MIT) - see LICENSE file
"""
# Modified for uasyncio operation Peter Hinch April 2018
# Portability:
# Replaced pyb with machine
# If machine not available assumed to be running under CPython (Raspberry Pi)
# time module assumed to return a float

# TODO:
# Time Since First Fix
# Distance/Time to Target
# More Helper Functions
# Dynamically limit sentences types to parse

from math import floor, modf
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

# Import utime or time for fix time handling
try:
    # Assume running on MicroPython
    import utime
except ImportError:
    # Otherwise default to time module for non-embedded implementations
    # Should still support millisecond resolution.
    import time


class MicropyGPS(object):
    """GPS NMEA Sentence Parser. Creates object that stores all relevant GPS data and statistics.
    Parses sentences by complete line using update(). """

    _SENTENCE_LIMIT = 76  # Max sentence length (based on GGA sentence)
    _HEMISPHERES = ('N', 'S', 'E', 'W')
    _NO_FIX = 1
    _FIX_2D = 2
    _FIX_3D = 3
    _DIRECTIONS = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W',
                    'WNW', 'NW', 'NNW')
    _MONTHS = ('January', 'February', 'March', 'April', 'May',
                'June', 'July', 'August', 'September', 'October',
                'November', 'December')

    def __init__(self, sreader, local_offset=0, fix_cb=lambda *_ : None, fix_cb_args=()):
        """
        Setup GPS Object Status Flags, Internal Data Registers, etc
            local_offset (int): Timzone Difference to UTC
            location_formatting (str): Style For Presenting Longitude/Latitude:
                                       Decimal Degree Minute (ddm) - 40° 26.767′ N
                                       Degrees Minutes Seconds (dms) - 40° 26′ 46″ N
                                       Decimal Degrees (dd) - 40.446° N
        """

        self.sreader = sreader  # None: in testing update is called with simulated data
        self.fix_cb = fix_cb
        self.fix_cb_args = fix_cb_args
        # All the currently supported NMEA sentences
        self.supported_sentences = {'GPRMC': self.gprmc, 'GLRMC': self.gprmc,
                                    'GPGGA': self.gpgga, 'GLGGA': self.gpgga,
                                    'GPVTG': self.gpvtg, 'GLVTG': self.gpvtg,
                                    'GPGSA': self.gpgsa, 'GLGSA': self.gpgsa,
                                    'GPGSV': self.gpgsv, 'GLGSV': self.gpgsv,
                                    'GPGLL': self.gpgll, 'GLGLL': self.gpgll,
                                    'GNGGA': self.gpgga, 'GNRMC': self.gprmc,
                                    'GNVTG': self.gpvtg,
                                    }

        #####################
        # Object Status Flags
        self.fix_time = None

        #####################
        # Sentence Statistics
        self.crc_fails = 0
        self.clean_sentences = 0
        self.parsed_sentences = 0

        #####################
        # Data From Sentences
        # Time
        self.timestamp = (0, 0, 0)
        self.date = (0, 0, 0)
        self.local_offset = local_offset

        # Position/Motion
        self._latitude = (0, 0.0, 'N')
        self._longitude = (0, 0.0, 'W')
        self.speed = (0.0, 0.0, 0.0)
        self.course = 0.0
        self.altitude = 0.0
        self.geoid_height = 0.0

        # GPS Info
        self.satellites_in_view = 0
        self.satellites_in_use = 0
        self.satellites_used = []
        self.last_sv_sentence = 0
        self.total_sv_sentences = 0
        self.satellite_data = dict()
        self.hdop = 0.0
        self.pdop = 0.0
        self.vdop = 0.0
        self.valid = False
        self.fix_stat = 0
        self.fix_type = 1
        if sreader is not None:  # Running with UART data
            loop = asyncio.get_event_loop()
            loop.create_task(self.run())

    ##########################################
    # Data Stream Handler Functions
    ##########################################


    async def run(self):
        while True:
            res = await self.sreader.readline()
#            print(res)
            self.update(res.decode('utf8'))

    # 8-bit xor of characters between "$" and "*"
    def crc_check(self, res, ascii_crc):
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

    # Update takes a line of text
    def update(self, line):
        line = line.rstrip()
        try:
            next(c for c in line if ord(c) < 10 or ord(c) > 126)
            return None  # Bad character received
        except StopIteration:
            pass

        if len(line) > self._SENTENCE_LIMIT:
            return None  # Too long

        if not '*' in line:
            return None

        a = line.split(',')
        segs = a[:-1] + a[-1].split('*')
        if not self.crc_check(line, segs[-1]):
            self.crc_fails += 1
            return None

        self.clean_sentences += 1
        segs[0] = segs[0][1:]  # discard $
        if segs[0] in self.supported_sentences:
            if self.supported_sentences[segs[0]](segs):
                self.parsed_sentences += 1
                return segs[0]

    def new_fix_time(self):
        """Updates a high resolution counter with current time when fix is updated. Currently only triggered from
        GGA, GSA and RMC sentences"""
        try:
            self.fix_time = utime.ticks_ms()
        except NameError:
            self.fix_time = time.time()
        self.fix_cb(self, *self.fix_cb_args)  # Run the callback

    ########################################
    # Coordinates Translation Functions
    ########################################

    def latitude(self, coord_format=None):
        """Format Latitude Data Correctly"""
        if coord_format == 'dd':
            decimal_degrees = self._latitude[0] + (self._latitude[1] / 60)
            return [decimal_degrees, self._latitude[2]]
        elif coord_format == 'dms':
            minute_parts = modf(self._latitude[1])
            seconds = round(minute_parts[0] * 60)
            return [self._latitude[0], int(minute_parts[1]), seconds, self._latitude[2]]
        else:
            return self._latitude

    def longitude(self, coord_format=None):
        """Format Longitude Data Correctly"""
        if coord_format == 'dd':
            decimal_degrees = self._longitude[0] + (self._longitude[1] / 60)
            return [decimal_degrees, self._longitude[2]]
        elif coord_format == 'dms':
            minute_parts = modf(self._longitude[1])
            seconds = round(minute_parts[0] * 60)
            return [self._longitude[0], int(minute_parts[1]), seconds, self._longitude[2]]
        else:
            return self._longitude


    ########################################
    # Sentence Parsers
    ########################################
    def gprmc(self, gps_segments):
        """Parse Recommended Minimum Specific GPS/Transit data (RMC)Sentence.
        Updates UTC timestamp, latitude, longitude, Course, Speed, Date, and fix status
        """

        # UTC Timestamp. If time/date not present retain last reading (if any).
        try:
            utc_string = gps_segments[1]

            if utc_string:  # Possible timestamp found
                hours = int(utc_string[0:2]) + self.local_offset
                minutes = int(utc_string[2:4])
                seconds = float(utc_string[4:])
                self.timestamp = (hours, minutes, seconds)

        except ValueError:  # Bad Timestamp value present
            return False

        # Date stamp
        try:
            date_string = gps_segments[9]

            # Date string printer function assumes to be year >=2000,
            # date_string() must be supplied with the correct century argument to display correctly
            if date_string:  # Possible date stamp found
                day = int(date_string[0:2])
                month = int(date_string[2:4])
                year = int(date_string[4:6])
                self.date = (day, month, year)

        except ValueError:  # Bad Date stamp value present
            return False

        # Check Receiver Data Valid Flag
        if gps_segments[2] == 'A':  # Data from Receiver is Valid/Has Fix

            # Longitude / Latitude
            try:
                # Latitude
                l_string = gps_segments[3]
                lat_degs = int(l_string[0:2])
                lat_mins = float(l_string[2:])
                lat_hemi = gps_segments[4]

                # Longitude
                l_string = gps_segments[5]
                lon_degs = int(l_string[0:3])
                lon_mins = float(l_string[3:])
                lon_hemi = gps_segments[6]
            except ValueError:
                return False

            if lat_hemi not in self._HEMISPHERES:
                return False

            if lon_hemi not in self._HEMISPHERES:
                return False

            # Speed
            try:
                spd_knt = float(gps_segments[7])
            except ValueError:
                return False

            # Course
            try:
                course = float(gps_segments[8])
            except ValueError:
                return False

            # TODO - Add Magnetic Variation

            # Update Object Data
            self._latitude = (lat_degs, lat_mins, lat_hemi)
            self._longitude = (lon_degs, lon_mins, lon_hemi)
            # Include mph and hm/h
            self.speed = (spd_knt, spd_knt * 1.151, spd_knt * 1.852)
            self.course = course
            self.valid = True

            # Update Last Fix Time
            self.new_fix_time()

        else:  # Leave data unchanged if Sentence is 'Invalid'
            self.valid = False

        return True

    def gpgll(self, gps_segments):
        """Parse Geographic Latitude and Longitude (GLL)Sentence. Updates UTC timestamp, latitude,
        longitude, and fix status"""

        # UTC Timestamp. If time/date not present retain last reading (if any).
        try:
            utc_string = gps_segments[5]

            if utc_string:  # Possible timestamp found
                hours = int(utc_string[0:2]) + self.local_offset
                minutes = int(utc_string[2:4])
                seconds = float(utc_string[4:])
                self.timestamp = (hours, minutes, seconds)

        except ValueError:  # Bad Timestamp value present
            return False

        # Check Receiver Data Valid Flag
        if gps_segments[6] == 'A':  # Data from Receiver is Valid/Has Fix

            # Longitude / Latitude
            try:
                # Latitude
                l_string = gps_segments[1]
                lat_degs = int(l_string[0:2])
                lat_mins = float(l_string[2:])
                lat_hemi = gps_segments[2]

                # Longitude
                l_string = gps_segments[3]
                lon_degs = int(l_string[0:3])
                lon_mins = float(l_string[3:])
                lon_hemi = gps_segments[4]
            except ValueError:
                return False

            if lat_hemi not in self._HEMISPHERES:
                return False

            if lon_hemi not in self._HEMISPHERES:
                return False

            # Update Object Data
            self._latitude = (lat_degs, lat_mins, lat_hemi)
            self._longitude = (lon_degs, lon_mins, lon_hemi)
            self.valid = True

            # Update Last Fix Time
            self.new_fix_time()

        else:  # Leave data unchanged if Sentence is 'Invalid'
            self.valid = False

        return True

    def gpvtg(self, gps_segments):
        """Parse Track Made Good and Ground Speed (VTG) Sentence. Updates speed and course"""
        try:
            course = float(gps_segments[1])
            spd_knt = float(gps_segments[5])
        except ValueError:
            return False

        # Include mph and km/h
        self.speed = (spd_knt, spd_knt * 1.151, spd_knt * 1.852)
        self.course = course
        return True

    def gpgga(self, gps_segments):
        """Parse Global Positioning System Fix Data (GGA) Sentence. Updates UTC timestamp, latitude, longitude,
        fix status, satellites in use, Horizontal Dilution of Precision (HDOP), altitude, geoid height and fix status"""

        try:
            # UTC Timestamp
            utc_string = gps_segments[1]

            # Skip timestamp if receiver doesn't have one yet
            if utc_string:
                hms = (int(utc_string[0:2]) + self.local_offset,
                       int(utc_string[2:4]),
                       float(utc_string[4:]))
            else:
                hms = None

            # Number of Satellites in Use
            satellites_in_use = int(gps_segments[7])

            # Horizontal Dilution of Precision
            hdop = float(gps_segments[8])

            # Get Fix Status
            fix_stat = int(gps_segments[6])

        except ValueError:
            return False

        # Process Location and Speed Data if Fix is GOOD
        if fix_stat:

            # Longitude / Latitude
            try:
                # Latitude
                l_string = gps_segments[2]
                lat_degs = int(l_string[0:2])
                lat_mins = float(l_string[2:])
                lat_hemi = gps_segments[3]

                # Longitude
                l_string = gps_segments[4]
                lon_degs = int(l_string[0:3])
                lon_mins = float(l_string[3:])
                lon_hemi = gps_segments[5]
            except ValueError:
                return False

            if lat_hemi not in self._HEMISPHERES:
                return False

            if lon_hemi not in self._HEMISPHERES:
                return False

            # Altitude / Height Above Geoid
            try:
                altitude = float(gps_segments[9])
                geoid_height = float(gps_segments[11])
            except ValueError:
                return False

            # Update Object Data
            self._latitude = (lat_degs, lat_mins, lat_hemi)
            self._longitude = (lon_degs, lon_mins, lon_hemi)
            self.altitude = altitude
            self.geoid_height = geoid_height

        # Update Object Data
        if hms is not None:
            self.timestamp = hms
        self.satellites_in_use = satellites_in_use
        self.hdop = hdop
        self.fix_stat = fix_stat

        # If Fix is GOOD, update fix timestamp
        if fix_stat:
            self.new_fix_time()

        return True

    def gpgsa(self, gps_segments):
        """Parse GNSS DOP and Active Satellites (GSA) sentence. Updates GPS fix type, list of satellites used in
        fix calculation, Position Dilution of Precision (PDOP), Horizontal Dilution of Precision (HDOP), Vertical
        Dilution of Precision, and fix status"""

        # Fix Type (None,2D or 3D)
        try:
            fix_type = int(gps_segments[2])
        except ValueError:
            return False

        # Read All (up to 12) Available PRN Satellite Numbers
        sats_used = []
        for sats in range(12):
            sat_number_str = gps_segments[3 + sats]
            if sat_number_str:
                try:
                    sat_number = int(sat_number_str)
                    sats_used.append(sat_number)
                except ValueError:
                    return False
            else:
                break

        # PDOP,HDOP,VDOP
        try:
            pdop = float(gps_segments[15])
            hdop = float(gps_segments[16])
            vdop = float(gps_segments[17])
        except ValueError:
            return False

        # Update Object Data
        self.fix_type = fix_type

        # If Fix is GOOD, update fix timestamp
        if fix_type > self._NO_FIX:
            self.new_fix_time()

        self.satellites_used = sats_used
        self.hdop = hdop
        self.vdop = vdop
        self.pdop = pdop

        return True

    def gpgsv(self, gps_segments):
        """Parse Satellites in View (GSV) sentence. Updates number of SV Sentences,the number of the last SV sentence
        parsed, and data on each satellite present in the sentence"""
        try:
            num_sv_sentences = int(gps_segments[1])
            current_sv_sentence = int(gps_segments[2])
            sats_in_view = int(gps_segments[3])
        except ValueError:
            return False

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
                except (ValueError,IndexError):
                    return False

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
        self.total_sv_sentences = num_sv_sentences
        self.last_sv_sentence = current_sv_sentence
        self.satellites_in_view = sats_in_view

        # For a new set of sentences, we either clear out the existing sat data or
        # update it as additional SV sentences are parsed
        if current_sv_sentence == 1:
            self.satellite_data = satellite_dict
        else:
            self.satellite_data.update(satellite_dict)

        return True

    #########################################
    # User Helper Functions
    # These functions make working with the GPS object data easier
    #########################################

    def satellite_data_updated(self):
        """
        Checks if the all the GSV sentences in a group have been read, making satellite data complete
        :return: boolean
        """
        if self.total_sv_sentences > 0 and self.total_sv_sentences == self.last_sv_sentence:
            return True
        else:
            return False

    def satellites_visible(self):
        """
        Returns a list of of the satellite PRNs currently visible to the receiver
        :return: list
        """
        return list(self.satellite_data.keys())

    def time_since_fix(self):
        """Returns number of millisecond since the last sentence with a valid fix was parsed.
        Returns -1 if no fix has been found"""

        # Test if a Fix has been found
        if self.fix_time is None:
            return -1

        # Try calculating fix time using utime; default to seconds if not running MicroPython
        try:
            current = utime.ticks_diff(utime.ticks_ms(), self.fix_time)
        except NameError:
            current = (time.time() - self.fix_time) * 1000  # ms

        return current

    def compass_direction(self):
        """
        Determine a cardinal or inter-cardinal direction based on current course.
        :return: string
        """
        # Calculate the offset for a rotated compass
        if self.course >= 348.75:
            offset_course = 360 - self.course
        else:
            offset_course = self.course + 11.25

        # Each compass point is separated by 22.5 degrees, divide to find lookup value
        dir_index = floor(offset_course / 22.5)

        final_dir = self._DIRECTIONS[dir_index]

        return final_dir

    def latitude_string(self, coord_format=None):
        """
        Create a readable string of the current latitude data
        :return: string
        """
        if coord_format == 'dd':
            form_lat = self.latitude(coord_format)
            lat_string = str(form_lat[0]) + '° ' + str(self._latitude[2])
        elif coord_format == 'dms':
            form_lat = self.latitude(coord_format)
            lat_string = str(form_lat[0]) + '° ' + str(form_lat[1]) + "' " + str(form_lat[2]) + '" ' + str(form_lat[3])
        elif coord_format == 'kml':
            form_lat = self.latitude('dd')
            lat_string = str(form_lat[0] if self._latitude[2] == 'N' else -form_lat[0])
        else:
            lat_string = str(self._latitude[0]) + '° ' + str(self._latitude[1]) + "' " + str(self._latitude[2])
        return lat_string

    def longitude_string(self, coord_format=None):
        """
        Create a readable string of the current longitude data
        :return: string
        """
        if coord_format == 'dd':
            form_long = self.longitude(coord_format)
            lon_string = str(form_long[0]) + '° ' + str(self._longitude[2])
        elif coord_format == 'dms':
            form_long = self.longitude(coord_format)
            lon_string = str(form_long[0]) + '° ' + str(form_long[1]) + "' " + str(form_long[2]) + '" ' + str(form_long[3])
        elif coord_format == 'kml':
            form_long = self.longitude('dd')
            lon = form_long[0] if self._longitude[2] == 'E' else -form_long[0]
            lon_string = str(lon)
        else:
            lon_string = str(self._longitude[0]) + '° ' + str(self._longitude[1]) + "' " + str(self._longitude[2])
        return lon_string

    def speed_string(self, unit='kph'):
        """
        Creates a readable string of the current speed data in one of three units
        :param unit: string of 'kph','mph, or 'knot'
        :return:
        """
        if unit == 'mph':
            speed_string = str(self.speed[1]) + ' mph'

        elif unit == 'knot':
            if self.speed[0] == 1:
                unit_str = ' knot'
            else:
                unit_str = ' knots'
            speed_string = str(self.speed[0]) + unit_str

        else:
            speed_string = str(self.speed[2]) + ' km/h'

        return speed_string

    def date_string(self, formatting='s_mdy', century='20'):
        """
        Creates a readable string of the current date.
        Can select between long format: Januray 1st, 2014
        or two short formats:
        11/01/2014 (MM/DD/YYYY)
        01/11/2014 (DD/MM/YYYY)
        :param formatting: string 's_mdy', 's_dmy', or 'long'
        :param century: int delineating the century the GPS data is from (19 for 19XX, 20 for 20XX)
        :return: date_string  string with long or short format date
        """

        # Long Format Januray 1st, 2014
        if formatting == 'long':
            # Retrieve Month string from private set
            month = self._MONTHS[self.date[1] - 1]

            # Determine Date Suffix
            if self.date[0] in (1, 21, 31):
                suffix = 'st'
            elif self.date[0] in (2, 22):
                suffix = 'nd'
            elif self.date[0] == 3:
                suffix = 'rd'
            else:
                suffix = 'th'

            day = str(self.date[0]) + suffix  # Create Day String

            year = century + str(self.date[2])  # Create Year String

            date_string = month + ' ' + day + ', ' + year  # Put it all together

        else:
            # Add leading zeros to day string if necessary
            if self.date[0] < 10:
                day = '0' + str(self.date[0])
            else:
                day = str(self.date[0])

            # Add leading zeros to month string if necessary
            if self.date[1] < 10:
                month = '0' + str(self.date[1])
            else:
                month = str(self.date[1])

            # Add leading zeros to year string if necessary
            if self.date[2] < 10:
                year = '0' + str(self.date[2])
            else:
                year = str(self.date[2])

            # Build final string based on desired formatting
            if formatting == 's_dmy':
                date_string = day + '/' + month + '/' + year

            else:  # Default date format
                date_string = month + '/' + day + '/' + year

        return date_string


if __name__ == "__main__":
    pass
