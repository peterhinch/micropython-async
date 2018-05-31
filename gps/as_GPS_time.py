# as_GPS_time.py Test scripts for as_tGPS.py read-only driver.
# Using GPS for precision timing and for calibrating Pyboard RTC

# This is STM-specific: requires pyb module.
# Requires asyn.py from this repo.

# Copyright (c) 2018 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import pyb
import utime
import math
import asyn
import as_tGPS

# Hardware assumptions. Change as required.
PPS_PIN = pyb.Pin.board.X3
UART_ID = 4

print('Available tests:')
print('calibrate(minutes=5) Set and calibrate the RTC.')
print('drift(minutes=5) Repeatedly print the difference between RTC and GPS time.')
print('time(minutes=1) Print get_ms() and get_t_split values.')
print('usec(minutes=1) Measure accuracy of usec timer.')
print('Press ctrl-d to reboot after each test.')

# Setup for tests. Red LED toggles on fix, blue on PPS interrupt.
async def setup():
    red = pyb.LED(1)
    blue = pyb.LED(4)
    uart = pyb.UART(UART_ID, 9600, read_buf_len=200)
    sreader = asyncio.StreamReader(uart)
    pps_pin = pyb.Pin(PPS_PIN, pyb.Pin.IN)
    return as_tGPS.GPS_Timer(sreader, pps_pin, local_offset=1,
                             fix_cb=lambda *_: red.toggle(),
                             pps_cb=lambda *_: blue.toggle())

# Test terminator: task sets the passed event after the passed time.
async def killer(end_event, minutes):
    print('Will run for {} minutes.'.format(minutes))
    await asyncio.sleep(minutes * 60)
    end_event.set()

# ******** Calibrate and set the Pyboard RTC ********
async def do_cal(minutes):
    gps = await setup()
    await gps.calibrate(minutes)
    gps.close()

def calibrate(minutes=5):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_cal(minutes))

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
    print('Setting up GPS.')
    gps = await setup()
    print('Waiting for time data.')
    await gps.ready()
    terminate = asyn.Event()
    loop = asyncio.get_event_loop()
    loop.create_task(killer(terminate, minutes))
    print('Setting RTC.')
    await gps.set_rtc()
    print('Measuring drift.')
    change = await drift_test(terminate, gps)
    ush = int(60 * change/minutes)
    spa = int(ush * 365 * 24 / 1000000)
    print('Rate of change {}μs/hr {}secs/year'.format(ush, spa))
    gps.close()

def drift(minutes=5):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_drift(minutes))

# ******** Time printing demo ********
# Every 10s print the difference between GPS time and RTC time
async def do_time(minutes):
    fstr = '{}ms Time: {:02d}:{:02d}:{:02d}:{:06d}'
    print('Setting up GPS.')
    gps = await setup()
    print('Waiting for time data.')
    await gps.ready()
    print('Setting RTC.')
    await gps.set_rtc()
    terminate = asyn.Event()
    loop = asyncio.get_event_loop()
    loop.create_task(killer(terminate, minutes))
    while not terminate.is_set():
        await asyncio.sleep(1)
        # In a precision app, get the time list without allocation:
        t = gps.get_t_split()
        print(fstr.format(gps.get_ms(), t[0], t[1], t[2], t[3]))
    gps.close()

def time(minutes=1):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_time(minutes))

# ******** Measure accracy of μs clock ********
# At 9600 baud see occasional lag of up to 3ms followed by similar lead.
# This implies that the ISR is being disabled for that period (~3 chars).
# SD 584μs typical.
# Test produces better numbers at 57600 baud (SD 112μs)
# and better still at 10Hz update rate (SD 34μs). Why??
# Unsure why. Setting of .FULL_CHECK has no effect (as expected).

# Callback occurs in interrupt context
us_acquired = None
def us_cb(my_gps, tick, led):
    global us_acquired  # Time of previous PPS edge in ticks_us()
    if us_acquired is not None:
        # Trigger event. Pass time between PPS measured by utime.ticks_us()
        tick.set(utime.ticks_diff(my_gps.acquired, us_acquired))
    us_acquired = my_gps.acquired
    led.toggle()

# Setup initialises with above callback
async def us_setup(tick):
    red = pyb.LED(1)
    blue = pyb.LED(4)
    uart = pyb.UART(UART_ID, 9600, read_buf_len=200)
    sreader = asyncio.StreamReader(uart)
    pps_pin = pyb.Pin(PPS_PIN, pyb.Pin.IN)
    return as_tGPS.GPS_Timer(sreader, pps_pin, local_offset=1,
                             fix_cb=lambda *_: red.toggle(),
                             pps_cb=us_cb, pps_cb_args=(tick, blue))

async def do_usec(minutes):
    tick = asyn.Event()
    print('Setting up GPS.')
    gps = await us_setup(tick)
    print('Waiting for time data.')
    await gps.ready()
    max_us = 0
    min_us = 0
    sd = 0
    nsamples = 0
    count = 0
    terminate = asyn.Event()
    loop = asyncio.get_event_loop()
    loop.create_task(killer(terminate, minutes))
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
    gps.close()

def usec(minutes=1):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do_usec(minutes))
