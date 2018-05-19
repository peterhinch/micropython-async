# as_GPS_time.py Test scripts for as_tGPS
# Using GPS for precision timing and for calibrating Pyboard RTC
# This is STM-specific: requires pyb module.

# Copyright (c) 2018 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import pyb
import as_GPS
import as_tGPS

# Setup for tests. Red LED toggles on fix, blue on PPS interrupt.
async def setup():
    red = pyb.LED(1)
    blue = pyb.LED(4)
    uart = pyb.UART(4, 9600, read_buf_len=200)
    sreader = asyncio.StreamReader(uart)
    gps = as_GPS.AS_GPS(sreader, local_offset=1, fix_cb=lambda *_: red.toggle())
    pps_pin = pyb.Pin('X3', pyb.Pin.IN)
    return as_tGPS.GPS_Timer(gps, pps_pin, blue)

async def drift_test(gps_tim, minutes):
    for _ in range(minutes):
        for _ in range(6):
            dt = await gps_tim.delta()
            print(gps_tim.get_t_split(), end='')
            print('Delta {}'.format(dt))
            await asyncio.sleep(10)

# Calibrate and set the Pyboard RTC
async def do_cal(minutes):
    gps_tim = await setup()
    await gps_tim.calibrate(minutes)

def calibrate(minutes=5):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_cal(minutes))

# Every 10s print the difference between GPS time and RTC time
async def do_drift(minutes):
    gps_tim = await setup()
    await drift_test(gps_tim, minutes)

def drift(minutes=5):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_drift(minutes))
