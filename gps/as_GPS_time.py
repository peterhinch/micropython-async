# as_GPS_time.py Using GPS for precision timing and for calibrating Pyboard RTC
# This is STM-specific: requires pyb module.

# Current state: getcal seems to work but needs further testing (odd values ocasionally)
# Other API functions need testing

# Copyright (c) 2018 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import math
import pyb
import utime
import micropython
import as_GPS

micropython.alloc_emergency_exception_buf(100)

red, green, yellow, blue = pyb.LED(1), pyb.LED(2), pyb.LED(3), pyb.LED(4)
rtc = pyb.RTC()

# Convenience function. Return RTC seconds since midnight as float
def rtc_secs():
    dt = rtc.datetime()
    return 3600*dt[4] + 60*dt[5] + dt[6] + (255 - dt[7])/256

# Return day of week from date. Pyboard RTC format: 1-7 for Monday through Sunday.
# https://stackoverflow.com/questions/9847213/how-do-i-get-the-day-of-week-given-a-date-in-python?noredirect=1&lq=1
# Adapted for Python 3 and Pyboard RTC format.
def week_day(year, month, day):
    offset = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
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

class GPS_Timer():
    def __init__(self, gps, pps_pin):
        self.gps = gps
        self.secs = None  # Integer time since midnight at last PPS
        self.acquired = None  # Value of ticks_us at edge of PPS
        loop = asyncio.get_event_loop()
        loop.create_task(self._start(pps_pin))

    async def _start(self, pps_pin):
        await self.gps.data_received(date=True)
        pyb.ExtInt(pps_pin, pyb.ExtInt.IRQ_RISING, pyb.Pin.PULL_NONE, self._isr)
        print('ISR set up', self.gps.date, self.gps.timestamp)

    def _isr(self, _):
        t = self.gps.timestamp
        secs = 3600*t[0] + 60*t[1] + t[2]  # Time in last NMEA sentence
        # Could be an outage here, so PPS arrives many secs after last sentence
        # Is this right? Does PPS continue during outage?
        self.secs = secs + 1  # PPS preceeds NMEA so add 1 sec
        self.acquired = utime.ticks_us()
        blue.toggle()  # TEST

    # Return accurate GPS time in seconds (float) since midnight
    def get_secs(self):
        print(self.gps.timestamp)
        t = self.secs
        if t != self.secs:  # An interrupt has occurred
            t = self.secs  # IRQ's are at 1Hz so this must be OK
        return t + utime.ticks_diff(utime.ticks_us(), self.acquired) / 1000000

    # Return accurate GPS time of day (hrs <int>, mins <int>, secs<float>)
    def get_t_split(self):
        t = math.modf(self.get_secs())
        m, s = divmod(int(t[1]), 60)
        h = int(m // 60)
        return h, m, s + t[0]

    # Return a time/date tuple suitable for setting RTC
    def _get_td_split(self):
        d, m, y = self.gps.date
        t = math.modf(self.get_secs())
        m, s = divmod(int(t[1]), 60)
        h = int(m // 60)
        ss = int(255*(1 - t[0]))
        return y, m, d, week_day(y, m, d), h, m, s, ss

    def set_rtc(self):
        rtc.datetime(self._get_td_split())

    # Time from GPS: integer μs since Y2K. Call after awaiting PPS: result is
    # time when PPS leading edge occurred
    def _get_gps_usecs(self):
        d, m, y = self.gps.date
        t = math.modf(self.get_secs())
        mins, secs = divmod(int(t[1]), 60)
        hrs = int(mins // 60)
        print(y, m, d, t, hrs, mins, secs)
        tim = utime.mktime((2000 + y, m, d, hrs, mins, secs, week_day(y, m, d) - 1, 0))
        return tim * 1000000

    # Return no. of μs RTC leads GPS. Done by comparing times at the instant of
    # PPS leading edge.
    def delta(self):
        rtc_time = self._await_pps()  # μs since Y2K at time of PPS
        gps_time = self._get_gps_usecs()  # μs since Y2K at PPS
        return rtc_time - gps_time

    # Pause until PPS interrupt occurs. Then wait for an RTC subsecond change.
    # Read the RTC time in μs since Y2K and adjust to give the time the RTC
    # (notionally) would have read at the PPS leading edge.
    def _await_pps(self):
        t0 = self.acquired
        while self.acquired == t0:  # Busy-wait on PPS interrupt
            pass
        st = rtc.datetime()[7]
        while rtc.datetime()[7] == st:  # Wait for RTC to change
            pass
        dt = utime.ticks_diff(utime.ticks_us(), self.acquired)
        return 1000000 * utime.time() + ((1000000 * (255 - rtc.datetime()[7])) >> 8) - dt

    # Non-realtime calculation of calibration factor. times are in μs
    def _calculate(self, gps_start, gps_end, rtc_start, rtc_end):
        # Duration (μs) between PPS edges
        print('Calculate', gps_start, gps_end, rtc_start, rtc_end)
        pps_delta = (gps_end - gps_start)
        # Duration (μs) between PPS edges as measured by RTC and corrected
        rtc_delta = (rtc_end - rtc_start) 
        ppm = (1000000 * (rtc_delta - pps_delta)) / pps_delta  # parts per million
        return int(-ppm/0.954)

    # Measure difference between RTC and GPS rate and return calibration factor
    # Note this blocks for upto 1 sec at intervals
    async def getcal(self, minutes=5):
        if minutes < 1:
            raise ValueError('Minutes must be >= 1')
        rtc.calibration(0)  # Clear existing cal
        # Wait for PPS, then RTC 1/256 second change
        # return RTC time in μs since Y2K at instant of PPS
        rtc_start = self._await_pps()
        # GPS start time in μs since Y2K: co at time of PPS edge
        gps_start = self._get_gps_usecs()
        for n in range(minutes):
            for _ in range(6):
                await asyncio.sleep(10)  # TEST 60
                # Get RTC time at instant of PPS
                rtc_end = self._await_pps()
                gps_end = self._get_gps_usecs()
                cal = self._calculate(gps_start, gps_end, rtc_start, rtc_end)
                print('Mins {:d} cal factor {:d}'.format(n + 1, cal))
        return cal

    async def calibrate(self, minutes=5):
        print('Waiting for startup')
        while self.acquired is None:
            await asyncio.sleep(1)  # Wait for startup
        print('Waiting {} minutes to acquire calibration factor...'.format(minutes))
        cal = await self.getcal(minutes)
        if cal <= 512 and cal >= -511:
            rtc.calibration(cal)
            print('Pyboard RTC is calibrated. Factor is {:d}.'.format(cal))
        else:
            print('Calibration factor {:d} is out of range.'.format(cal))

# Test script. Red LED toggles on fix, Blue on PPS interrupt.
async def run_test(minutes):
    uart = pyb.UART(4, 9600, read_buf_len=200)
    sreader = asyncio.StreamReader(uart)
    gps = as_GPS.AS_GPS(sreader, fix_cb=lambda *_: red.toggle())
    pps_pin = pyb.Pin('X3', pyb.Pin.IN)
    gps_tim = GPS_Timer(gps, pps_pin)
    await gps_tim.calibrate(minutes)

def test(minutes=5):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_test(minutes))
