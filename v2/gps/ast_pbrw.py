# ast_pb.py
# Basic test/demo of AS_GPS class (asynchronous GPS device driver)
# Runs on a Pyboard with GPS data on pin X2.
# Copyright (c) Peter Hinch 2018
# Released under the MIT License (MIT) - see LICENSE file
# Test asynchronous GPS device driver as_rwGPS

# LED's:
# Green indicates data is being received.
# Red toggles on RMC message received.
# Yellow and blue: coroutines have 4s loop delay.
# Yellow toggles on position reading.
# Blue toggles on date valid.

import pyb
import uasyncio as asyncio
import aswitch
import as_GPS
import as_rwGPS

# Avoid multiple baudrates. Tests use 9600 or 19200 only.
BAUDRATE = 19200
red, green, yellow = pyb.LED(1), pyb.LED(2), pyb.LED(3)
ntimeouts = 0

def callback(gps, _, timer):
    red.toggle()
    green.on()
    timer.trigger(10000)  # Outage is declared after 10s

def cb_timeout():
    global ntimeouts
    green.off()
    ntimeouts += 1

def message_cb(gps, segs):
    print('Message received:', segs)

# Print satellite data every 10s
async def sat_test(gps):
    while True:
        d = await gps.get_satellite_data()
        print('***** SATELLITE DATA *****')
        print('Data is Valid:', hex(gps._valid))
        for i in d:
            print(i, d[i])
        print()
        await asyncio.sleep(10)

# Print statistics every 30s
async def stats(gps):
    while True:
        await gps.data_received(position=True)  # Wait for a valid fix
        await asyncio.sleep(30)
        print('***** STATISTICS *****')
        print('Outages:', ntimeouts)
        print('Sentences Found:', gps.clean_sentences)
        print('Sentences Parsed:', gps.parsed_sentences)
        print('CRC_Fails:', gps.crc_fails)
        print('Antenna status:', gps.antenna)
        print('Firmware vesrion:', gps.version)
        print('Enabled sentences:', gps.enabled)
        print()

# Print navigation data every 4s
async def navigation(gps):
    while True:
        await asyncio.sleep(4)
        await gps.data_received(position=True)
        yellow.toggle()
        print('***** NAVIGATION DATA *****')
        print('Data is Valid:', hex(gps._valid))
        print('Longitude:', gps.longitude(as_GPS.DD))
        print('Latitude', gps.latitude(as_GPS.DD))
        print()

async def course(gps):
    while True:
        await asyncio.sleep(4)
        await gps.data_received(course=True)
        print('***** COURSE DATA *****')
        print('Data is Valid:', hex(gps._valid))
        print('Speed:', gps.speed_string(as_GPS.MPH))
        print('Course', gps.course)
        print('Compass Direction:', gps.compass_direction())
        print()

async def date(gps):
    while True:
        await asyncio.sleep(4)
        await gps.data_received(date=True)
        print('***** DATE AND TIME *****')
        print('Data is Valid:', hex(gps._valid))
        print('UTC Time:', gps.utc)
        print('Local time:', gps.local_time)
        print('Date:', gps.date_string(as_GPS.LONG))
        print()

async def change_status(gps, uart):
    await asyncio.sleep(10)
    print('***** Changing status. *****')
    await gps.baudrate(BAUDRATE)
    uart.init(BAUDRATE)
    print('***** baudrate 19200 *****')
    await asyncio.sleep(5)  # Ensure baudrate is sorted
    print('***** Query VERSION *****')
    await gps.command(as_rwGPS.VERSION)
    await asyncio.sleep(10)
    print('***** Query ENABLE *****')
    await gps.command(as_rwGPS.ENABLE)
    await asyncio.sleep(10)  # Allow time for 1st report
    await gps.update_interval(2000)
    print('***** Update interval 2s *****')
    await asyncio.sleep(10)
    await gps.enable(gsv = False, chan = False)
    print('***** Disable satellite in view and channel messages *****')
    await asyncio.sleep(10)
    print('***** Query ENABLE *****')
    await gps.command(as_rwGPS.ENABLE)

# See README.md re antenna commands
#    await asyncio.sleep(10)
#    await gps.command(as_rwGPS.ANTENNA)
#    print('***** Antenna reports requested *****')
#    await asyncio.sleep(60)
#    await gps.command(as_rwGPS.NO_ANTENNA)
#    print('***** Antenna reports turned off *****')
#    await asyncio.sleep(10)

async def gps_test():
    global gps, uart  # For shutdown
    print('Initialising')
    # Adapt UART instantiation for other MicroPython hardware
    uart = pyb.UART(4, 9600, read_buf_len=200)
    # read_buf_len is precautionary: code runs reliably without it.
    sreader = asyncio.StreamReader(uart)
    swriter = asyncio.StreamWriter(uart, {})
    timer = aswitch.Delay_ms(cb_timeout)
    sentence_count = 0
    gps = as_rwGPS.GPS(sreader, swriter, local_offset=1, fix_cb=callback,
                       fix_cb_args=(timer,),  msg_cb = message_cb)
    await asyncio.sleep(2)
    await gps.command(as_rwGPS.DEFAULT_SENTENCES)
    print('Set sentence frequencies to default')
    #await gps.command(as_rwGPS.FULL_COLD_START)
    #print('Performed FULL_COLD_START')
    print('awaiting first fix')
    loop = asyncio.get_event_loop()
    loop.create_task(sat_test(gps))
    loop.create_task(stats(gps))
    loop.create_task(navigation(gps))
    loop.create_task(course(gps))
    loop.create_task(date(gps))
    await gps.data_received(True, True, True, True)  # all messages
    loop.create_task(change_status(gps, uart))

async def shutdown():
    # Normally UART is already at BAUDRATE. But if last session didn't restore
    # factory baudrate we can restore connectivity in the subsequent stuck
    # session with ctrl-c.
    uart.init(BAUDRATE)
    await asyncio.sleep(1)
    await gps.command(as_rwGPS.FULL_COLD_START)
    print('Factory reset')
    #print('Restoring default baudrate.')
    #await gps.baudrate(9600)

loop = asyncio.get_event_loop()
loop.create_task(gps_test())
try:
    loop.run_forever()
finally:
    loop.run_until_complete(shutdown())
