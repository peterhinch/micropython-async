# as_GPS_time.py Test scripts for as_tGPS
# Using GPS for precision timing and for calibrating Pyboard RTC
# This is STM-specific: requires pyb module.

# Copyright (c) 2018 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import pyb
import as_GPS
import as_tGPS

print('Available tests:')
print('calibrate(minutes=5) Set and calibrate the RTC.')
print('drift(minutes=5) Repeatedly print the difference between RTC and GPS time.')
print('time(minutes=1) Print get_ms() and get_t_split values.')

# Setup for tests. Red LED toggles on fix, blue on PPS interrupt.
async def setup():
    red = pyb.LED(1)
    blue = pyb.LED(4)
    uart = pyb.UART(4, 9600, read_buf_len=200)
    sreader = asyncio.StreamReader(uart)
    gps = as_GPS.AS_GPS(sreader, local_offset=1, fix_cb=lambda *_: red.toggle())
    pps_pin = pyb.Pin('X3', pyb.Pin.IN)
    return as_tGPS.GPS_Timer(gps, pps_pin, blue)

running = True

async def killer(minutes):
    global running
    await asyncio.sleep(minutes * 60)
    running = False

async def drift_test(gps_tim):
    dstart = await gps_tim.delta()
    while running:
        dt = await gps_tim.delta()
        print('{}  Delta {}μs'.format(gps_tim.gps.time_string(), dt))
        await asyncio.sleep(10)
    return dt - dstart

# Calibrate and set the Pyboard RTC
async def do_cal(minutes):
    gps_tim = await setup()
    await gps_tim.calibrate(minutes)

def calibrate(minutes=5):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_cal(minutes))

# Every 10s print the difference between GPS time and RTC time
async def do_drift(minutes):
    print('Setting up GPS.')
    gps_tim = await setup()
    print('Waiting for time data.')
    await gps_tim.ready()
    print('Setting RTC.')
    await gps_tim.set_rtc()
    print('Measuring drift.')
    change = await drift_test(gps_tim)
    ush = int(60 * change/minutes)
    spa = int(ush * 365 * 24 / 1000000)
    print('Rate of change {}μs/hr {}secs/year'.format(ush, spa))

def drift(minutes=5):
    global running
    running = True
    loop = asyncio.get_event_loop()
    loop.create_task(killer(minutes))
    loop.run_until_complete(do_drift(minutes))

# Every 10s print the difference between GPS time and RTC time
async def do_time(minutes):
    print('Setting up GPS.')
    gps_tim = await setup()
    print('Waiting for time data.')
    await gps_tim.ready()
    print('Setting RTC.')
    await gps_tim.set_rtc()
    while running:
        await asyncio.sleep(1)
        hrs, mins, secs, us = gps_tim.get_t_split()
        print('{}ms Time: {:02d}:{:02d}:{:02d}:{:06d}'.format(gps_tim.get_ms(), hrs, mins, secs, us))

def time(minutes=1):
    global running
    running = True
    loop = asyncio.get_event_loop()
    loop.create_task(killer(minutes))
    loop.run_until_complete(do_time(minutes))
