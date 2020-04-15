# astests_pyb.py

# Tests for AS_GPS module. Emulates a GPS unit using a UART loopback.
# Run on a Pyboard with X1 and X2 linked
# Tests for AS_GPS module (asynchronous GPS device driver)
# Based on tests for MicropyGPS by Michael Calvin McCoy
# https://github.com/inmcm/micropyGPS

# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Ported to uasyncio V3 OK.

from .as_GPS import *
from machine import UART
import uasyncio as asyncio

def callback(gps, _, arg):
    print('Fix callback. Time:', gps.utc, arg)

async def run_tests():
    uart = UART(4, 9600, read_buf_len=200)
    swriter = asyncio.StreamWriter(uart, {})
    sreader = asyncio.StreamReader(uart)
    sentence_count = 0

    test_RMC = ['$GPRMC,180041.896,A,3749.1851,N,08338.7891,W,001.9,154.9,240911,,,A*7A\n',
                '$GPRMC,180049.896,A,3749.1808,N,08338.7869,W,001.8,156.3,240911,,,A*70\n',
                '$GPRMC,092751.000,A,5321.6802,N,00630.3371,W,0.06,31.66,280511,,,A*45\n']

    test_VTG = ['$GPVTG,232.9,T,,M,002.3,N,004.3,K,A*01\n']
    test_GGA = ['$GPGGA,180050.896,3749.1802,N,08338.7865,W,1,07,1.1,397.4,M,-32.5,M,,0000*6C\n']
    test_GSA = ['$GPGSA,A,3,07,11,28,24,26,08,17,,,,,,2.0,1.1,1.7*37\n',
                '$GPGSA,A,3,07,02,26,27,09,04,15,,,,,,1.8,1.0,1.5*33\n']
    test_GSV = ['$GPGSV,3,1,12,28,72,355,39,01,52,063,33,17,51,272,44,08,46,184,38*74\n',
                '$GPGSV,3,2,12,24,42,058,33,11,34,053,33,07,20,171,40,20,15,116,*71\n',
                '$GPGSV,3,3,12,04,12,204,34,27,11,324,35,32,11,089,,26,10,264,40*7B\n',
                '$GPGSV,3,1,11,03,03,111,00,04,15,270,00,06,01,010,00,13,06,292,00*74\n',
                '$GPGSV,3,2,11,14,25,170,00,16,57,208,39,18,67,296,40,19,40,246,00*74\n',
                '$GPGSV,3,3,11,22,42,067,42,24,14,311,43,27,05,244,00,,,,*4D\n',
                '$GPGSV,4,1,14,22,81,349,25,14,64,296,22,18,54,114,21,51,40,212,*7D\n',
                '$GPGSV,4,2,14,24,30,047,22,04,22,312,26,31,22,204,,12,19,088,23*72\n',
                '$GPGSV,4,3,14,25,17,127,18,21,16,175,,11,09,315,16,19,05,273,*72\n',
                '$GPGSV,4,4,14,32,05,303,,15,02,073,*7A\n']
    test_GLL = ['$GPGLL,3711.0942,N,08671.4472,W,000812.000,A,A*46\n',
                '$GPGLL,4916.45,N,12311.12,W,225444,A,*1D\n',
                '$GPGLL,4250.5589,S,14718.5084,E,092204.999,A*2D\n',
                '$GPGLL,4250.5589,S,14718.5084,E,092204.999,A*2D\n',]

#                '$GPGLL,0000.0000,N,00000.0000,E,235947.000,V*2D\n',  # Will ignore this one

    my_gps = AS_GPS(sreader, fix_cb=callback, fix_cb_args=(42,))
    sentence = ''
    for sentence in test_RMC:
        sentence_count += 1
        await swriter.awrite(sentence)
        await my_gps.data_received(date=True)
        print('Longitude:', my_gps.longitude())
        print('Latitude', my_gps.latitude())
        print('UTC Time:', my_gps.utc)
        print('Speed:', my_gps.speed())
        print('Date Stamp:', my_gps.date)
        print('Course', my_gps.course)
        print('Data is Valid:', my_gps._valid)
        print('Compass Direction:', my_gps.compass_direction())
        print('')

    for sentence in test_GLL:
        sentence_count += 1
        await swriter.awrite(sentence)
        await my_gps.data_received(position=True)
        print('Longitude:', my_gps.longitude())
        print('Latitude', my_gps.latitude())
        print('UTC Time:', my_gps.utc)
        print('Data is Valid:', my_gps._valid)
        print('')

    for sentence in test_VTG:
        print('Test VTG', sentence)
        sentence_count += 1
        await swriter.awrite(sentence)
        await asyncio.sleep_ms(200)  # Can't wait for course because of position check
        print('Speed:', my_gps.speed())
        print('Course', my_gps.course)
        print('Compass Direction:', my_gps.compass_direction())
        print('')

    for sentence in test_GGA:
        sentence_count += 1
        await swriter.awrite(sentence)
        await my_gps.data_received(position=True)
        print('Longitude', my_gps.longitude())
        print('Latitude', my_gps.latitude())
        print('UTC Time:', my_gps.utc)
#        print('Fix Status:', my_gps.fix_stat)
        print('Altitude:', my_gps.altitude)
        print('Height Above Geoid:', my_gps.geoid_height)
        print('Horizontal Dilution of Precision:', my_gps.hdop)
        print('Satellites in Use by Receiver:', my_gps.satellites_in_use)
        print('')

    for sentence in test_GSA:
        sentence_count += 1
        await swriter.awrite(sentence)
        await asyncio.sleep_ms(200)
        print('Satellites Used', my_gps.satellites_used)
        print('Horizontal Dilution of Precision:', my_gps.hdop)
        print('Vertical Dilution of Precision:', my_gps.vdop)
        print('Position Dilution of Precision:', my_gps.pdop)
        print('')

    for sentence in test_GSV:
        sentence_count += 1
        await swriter.awrite(sentence)
        await asyncio.sleep_ms(200)
        print('SV Sentences Parsed', my_gps._last_sv_sentence)
        print('SV Sentences in Total', my_gps._total_sv_sentences)
        print('# of Satellites in View:', my_gps.satellites_in_view)
        data_valid = my_gps._total_sv_sentences > 0 and my_gps._total_sv_sentences == my_gps._last_sv_sentence
        print('Is Satellite Data Valid?:', data_valid)
        if data_valid:
            print('Satellite Data:', my_gps._satellite_data)
            print('Satellites Visible:', list(my_gps._satellite_data.keys()))
        print('')

    print("Pretty Print Examples:")
    print('Latitude (degs):', my_gps.latitude_string(DD))
    print('Longitude (degs):', my_gps.longitude_string(DD))
    print('Latitude (dms):', my_gps.latitude_string(DMS))
    print('Longitude (dms):', my_gps.longitude_string(DMS))
    print('Latitude (kml):', my_gps.latitude_string(KML))
    print('Longitude (kml):', my_gps.longitude_string(KML))
    print('Latitude (degs, mins):', my_gps.latitude_string())
    print('Longitude (degs, mins):', my_gps.longitude_string())
    print('Speed:', my_gps.speed_string(KPH), 'or',
          my_gps.speed_string(MPH), 'or',
          my_gps.speed_string(KNOT))
    print('Date (Long Format):', my_gps.date_string(LONG))
    print('Date (Short D/M/Y Format):', my_gps.date_string(DMY))
    print('Date (Short M/D/Y Format):', my_gps.date_string(MDY))
    print('Time:', my_gps.time_string())
    print()

    print('### Final Results ###')
    print('Sentences Attempted:', sentence_count)
    print('Sentences Found:', my_gps.clean_sentences)
    print('Sentences Parsed:', my_gps.parsed_sentences)
    print('Unsupported sentences:', my_gps.unsupported_sentences)
    print('CRC_Fails:', my_gps.crc_fails)

asyncio.run(run_tests())
