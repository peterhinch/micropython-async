# as_rwGPS_time.py Test scripts for as_tGPS read-write driver.
# Using GPS for precision timing and for calibrating Pyboard RTC
# This is STM-specific: requires pyb module.

# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# See README.md notes re setting baudrates. In particular 9600 does not work.
# So these tests issue a factory reset on completion to restore the baudrate.

# String sent for 9600: $PMTK251,9600*17\r\n
# Data has (for 38400): $PMTK251,38400*27<CR><LF>
# Sending: $PMTK251,38400*27\r\n'

import uasyncio as asyncio
from uasyncio import Event
from primitives.message import Message
import pyb
import utime
import math
from .as_tGPS import GPS_RWTimer
from .as_rwGPS import FULL_COLD_START

# Hardware assumptions. Change as required.
PPS_PIN = pyb.Pin.board.X3
UART_ID = 4

BAUDRATE = 57600
UPDATE_INTERVAL = 100
READ_BUF_LEN = 200

print('Available tests:')
print('calibrate(minutes=5) Set and calibrate the RTC.')
print('drift(minutes=5) Repeatedly print the difference between RTC and GPS time.')
print('time(minutes=1) Print get_ms() and get_t_split values.')
print('usec(minutes=1) Measure accuracy of usec timer.')
print('Press ctrl-d to reboot after each test.')

# Initially use factory baudrate
uart = pyb.UART(UART_ID, 9600, read_buf_len=READ_BUF_LEN)

async def shutdown():
    global gps
    # Normally UART is already at BAUDRATE. But if last session didn't restore
    # factory baudrate we can restore connectivity in the subsequent stuck
    # session with ctrl-c.
    uart.init(BAUDRATE)
    await asyncio.sleep(0.5)
    await gps.command(FULL_COLD_START)
    print('Factory reset')
    gps.close()  # Stop ISR
    #print('Restoring default baudrate (9600).')
    #await gps.baudrate(9600)
    #uart.init(9600)
    #gps.close()  # Stop ISR
    #print('Restoring default 1s update rate.')
    #await asyncio.sleep(0.5)
    #await gps.update_interval(1000)  # 1s update rate 
    #print('Restoring satellite data.')
    #await gps.command(as_rwGPS.DEFAULT_SENTENCES)  # Restore satellite data

# Setup for tests. Red LED toggles on fix, blue on PPS interrupt.
async def setup():
    global uart, gps  # For shutdown
    red = pyb.LED(1)
    blue = pyb.LED(4)
    sreader = asyncio.StreamReader(uart)
    swriter = asyncio.StreamWriter(uart, {})
    pps_pin = pyb.Pin(PPS_PIN, pyb.Pin.IN)
    gps = GPS_RWTimer(sreader, swriter, pps_pin, local_offset=1,
                             fix_cb=lambda *_: red.toggle(),
                             pps_cb=lambda *_: blue.toggle())
    gps.FULL_CHECK = False
    await asyncio.sleep(2)
    await gps.baudrate(BAUDRATE)
    uart.init(BAUDRATE)
    await asyncio.sleep(1)
    await gps.enable(gsa=0, gsv=0)  # Disable satellite data
    await gps.update_interval(UPDATE_INTERVAL)
    pstr = 'Baudrate {} update interval {}ms satellite messages disabled.'
    print(pstr.format(BAUDRATE, UPDATE_INTERVAL))
    return gps

# Test terminator: task sets the passed event after the passed time.
async def killer(end_event, minutes):
    print('Will run for {} minutes.'.format(minutes))
    await asyncio.sleep(minutes * 60)
    end_event.set()

# ******** Calibrate and set the Pyboard RTC ********
async def do_cal(minutes):
    gps = await setup()
    await gps.calibrate(minutes)

def calibrate(minutes=5):
    try:
        asyncio.run(do_cal(minutes))
    finally:
        asyncio.run(shutdown())

# ******** Drift test ********
# Every 10s print the difference between GPS time and RTC time
async def drift_test(terminate, gps):
    dstart = await gps.delta()
    while not terminate.is_set():
        dt = await gps.delta()
        print('{}  Delta {}μs'.format(gps.time_string(), dt))
        await asyncio.sleep(10)
    return dt - dstart

async def do_drift(minutes):
    global gps
    print('Setting up GPS.')
    gps = await setup()
    print('Waiting for time data.')
    await gps.ready()
    print('Setting RTC.')
    await gps.set_rtc()
    print('Measuring drift.')
    terminate = Event()
    asyncio.create_task(killer(terminate, minutes))
    change = await drift_test(terminate, gps)
    ush = int(60 * change/minutes)
    spa = int(ush * 365 * 24 / 1000000)
    print('Rate of change {}μs/hr {}secs/year'.format(ush, spa))

def drift(minutes=5):
    try:
        asyncio.run(do_drift(minutes))
    finally:
        asyncio.run(shutdown())

# ******** Time printing demo ********
# Every 10s print the difference between GPS time and RTC time
async def do_time(minutes):
    global gps
    fstr = '{}ms Time: {:02d}:{:02d}:{:02d}:{:06d}'
    print('Setting up GPS.')
    gps = await setup()
    print('Waiting for time data.')
    await gps.ready()
    print('Setting RTC.')
    await gps.set_rtc()
    print('RTC is set.')
    terminate = Event()
    asyncio.create_task(killer(terminate, minutes))
    while not terminate.is_set():
        await asyncio.sleep(1)
        # In a precision app, get the time list without allocation:
        t = gps.get_t_split()
        print(fstr.format(gps.get_ms(), t[0], t[1], t[2], t[3]))

def time(minutes=1):
    try:
        asyncio.run(do_time(minutes))
    finally:
        asyncio.run(shutdown())

# ******** Measure accracy of μs clock ********
# Test produces better numbers at 57600 baud (SD 112μs)
# and better still at 10Hz update rate (SD 34μs).
# Unsure why.

# Callback occurs in interrupt context
us_acquired = None  # Time of previous PPS edge in ticks_us()
def us_cb(my_gps, tick, led):
    global us_acquired
    if us_acquired is not None:
        # Trigger event. Pass time between PPS measured by utime.ticks_us()
        tick.set(utime.ticks_diff(my_gps.acquired, us_acquired))
    us_acquired = my_gps.acquired
    led.toggle()

# Setup initialises with above callback
async def us_setup(tick):
    global uart, gps  # For shutdown
    red = pyb.LED(1)
    blue = pyb.LED(4)
    sreader = asyncio.StreamReader(uart)
    swriter = asyncio.StreamWriter(uart, {})
    pps_pin = pyb.Pin(PPS_PIN, pyb.Pin.IN)
    gps = GPS_RWTimer(sreader, swriter, pps_pin, local_offset=1,
                             fix_cb=lambda *_: red.toggle(),
                             pps_cb=us_cb, pps_cb_args=(tick, blue))
    gps.FULL_CHECK = False
    await asyncio.sleep(2)
    await gps.baudrate(BAUDRATE)
    uart.init(BAUDRATE)
    await asyncio.sleep(1)
    await gps.enable(gsa=0, gsv=0)  # Disable satellite data
    await gps.update_interval(UPDATE_INTERVAL)
    pstr = 'Baudrate {} update interval {}ms satellite messages disabled.'
    print(pstr.format(BAUDRATE, UPDATE_INTERVAL))

async def do_usec(minutes):
    global gps
    tick = Message()
    print('Setting up GPS.')
    await us_setup(tick)
    print('Waiting for time data.')
    await gps.ready()
    max_us = 0
    min_us = 0
    sd = 0
    nsamples = 0
    count = 0
    terminate = Event()
    asyncio.create_task(killer(terminate, minutes))
    while not terminate.is_set():
        await tick
        usecs = tick.value()
        tick.clear()
        err = 1000000 - usecs
        count += 1
        print('Timing discrepancy is {:4d}μs {}'.format(err, '(skipped)' if count < 3 else ''))
        if count < 3:  # Discard 1st two samples from statistics
            continue  # as these can be unrepresentative
        max_us = max(max_us, err)
        min_us = min(min_us, err)
        sd += err * err
        nsamples += 1
    # SD: apply Bessel's correction for infinite population
    sd = int(math.sqrt(sd/(nsamples - 1)))
    print('Timing discrepancy is: {:5d}μs max {:5d}μs min.  Standard deviation {:4d}μs'.format(max_us, min_us, sd))

def usec(minutes=1):
    try:
        asyncio.run(do_usec(minutes))
    finally:
        asyncio.run(shutdown())
