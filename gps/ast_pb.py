# ast_pb.py
# Basic test/demo of AS_GPS class (asynchronous GPS device driver)
# Runs on a Pyboard with GPS data on pin X2.
# Copyright (c) Peter Hinch 2018-2020
# Released under the MIT License (MIT) - see LICENSE file
# Test asynchronous GPS device driver as_pyGPS

import pyb
import uasyncio as asyncio
import aswitch
import as_GPS

red = pyb.LED(1)
green = pyb.LED(2)
ntimeouts = 0

def callback(gps, _, timer):
    red.toggle()
    green.on()
    timer.trigger(10000)

def timeout():
    global ntimeouts
    green.off()
    ntimeouts += 1

# Print satellite data every 10s
async def sat_test(gps):
    while True:
        d = await gps.get_satellite_data()
        print('***** SATELLITE DATA *****')
        for i in d:
            print(i, d[i])
        print()
        await asyncio.sleep(10)

# Print statistics every 30s
async def stats(gps):
    while True:
        await asyncio.sleep(30)
        print('***** STATISTICS *****')
        print('Outages:', ntimeouts)
        print('Sentences Found:', gps.clean_sentences)
        print('Sentences Parsed:', gps.parsed_sentences)
        print('CRC_Fails:', gps.crc_fails)
        print()

# Print navigation data every 4s
async def navigation(gps):
    while True:
        await asyncio.sleep(4)
        await gps.data_received(position=True)
        print('***** NAVIGATION DATA *****')
        print('Data is Valid:', gps._valid)
        print('Longitude:', gps.longitude(as_GPS.DD))
        print('Latitude', gps.latitude(as_GPS.DD))
        print()

async def course(gps):
    while True:
        await asyncio.sleep(4)
        await gps.data_received(course=True)
        print('***** COURSE DATA *****')
        print('Data is Valid:', gps._valid)
        print('Speed:', gps.speed_string(as_GPS.MPH))
        print('Course', gps.course)
        print('Compass Direction:', gps.compass_direction())
        print()

async def date(gps):
    while True:
        await asyncio.sleep(4)
        await gps.data_received(date=True)
        print('***** DATE AND TIME *****')
        print('Data is Valid:', gps._valid)
        print('UTC time:', gps.utc)
        print('Local time:', gps.local_time)
        print('Date:', gps.date_string(as_GPS.LONG))
        print()

async def gps_test():
    print('Initialising')
    # Adapt for other MicroPython hardware
    uart = pyb.UART(4, 9600, read_buf_len=200)
    # read_buf_len is precautionary: code runs reliably without it.)
    sreader = asyncio.StreamReader(uart)
    timer = aswitch.Delay_ms(timeout)
    sentence_count = 0
    gps = as_GPS.AS_GPS(sreader, local_offset=1, fix_cb=callback, fix_cb_args=(timer,))
    loop = asyncio.get_event_loop()
    print('awaiting first fix')
    loop.create_task(sat_test(gps))
    loop.create_task(stats(gps))
    loop.create_task(navigation(gps))
    loop.create_task(course(gps))
    loop.create_task(date(gps))


loop = asyncio.get_event_loop()
loop.create_task(gps_test())
loop.run_forever()
