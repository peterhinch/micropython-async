# as_GPS_utils.py Extra functionality for as_GPS.py
# Put in separate file to minimise size of as_GPS.py for resource constrained
# systems.

# Copyright (c) 2018 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file
from .as_GPS import MDY, DMY, LONG

_DIRECTIONS = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW',
               'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW')

def compass_direction(gps):  # Return cardinal point as string.
    # Calculate the offset for a rotated compass
    if gps.course >= 348.75:
        offset_course = 360 - gps.course
    else:
        offset_course = gps.course + 11.25
    # Each compass point is separated by 22.5°, divide to find lookup value
    return _DIRECTIONS[int(offset_course // 22.5)]

_MONTHS = ('January', 'February', 'March', 'April', 'May',
            'June', 'July', 'August', 'September', 'October',
            'November', 'December')

def date_string(gps, formatting=MDY):
    day, month, year = gps.date
    # Long Format January 1st, 2014
    if formatting == LONG:
        dform = '{:s} {:2d}{:s}, 20{:2d}'
        # Retrieve Month string from private set
        month = _MONTHS[month - 1]
        # Determine Date Suffix
        if day in (1, 21, 31):
            suffix = 'st'
        elif day in (2, 22):
            suffix = 'nd'
        elif day in (3, 23):
            suffix = 'rd'
        else:
            suffix = 'th'
        return dform.format(month, day, suffix, year)

    dform = '{:02d}/{:02d}/{:02d}'
    if formatting == DMY:
        return dform.format(day, month, year)
    elif formatting == MDY:  # Default date format
        return dform.format(month, day, year)
    raise ValueError('Unknown date format.')
