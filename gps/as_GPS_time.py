# as_GPS_time.py Using GPS for precision timing and for calibrating Pyboard RTC
# This is STM-specific: requires pyb module.

# Current state: getcal works but has a HACK due to a realtime issue I haven't yet diagnosed.
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

    def _isr(self, _):
        # Time in last NMEA sentence
        t = self.gps.timestamp
        # secs is rounded down to an int: exact time of last PPS
        secs = 3600*t[0] + 60*t[1] + int(t[2])
        # Could be an outage here, so PPS arrives many secs after last sentence
        # Is this right? Does PPS continue during outage?
        self.secs = secs + 1  # PPS preceeds NMEA so add 1 sec
        self.acquired = utime.ticks_us()
        blue.toggle()  # TEST

    # Return accurate GPS time in seconds (float) since midnight
    def get_secs(self):
        t = self.secs
        if t != self.secs:  # An interrupt has occurred
            # Re-read to ensure .acquired is correct. No need to get clever
            t = self.secs  # here as IRQ's are at only 1Hz
        return t + utime.ticks_diff(utime.ticks_us(), self.acquired) / 1000000

    # Return GPS time as hrs: int, mins: int, secs: int, fractional_secs: float
    def _get_hms(self):
        t = math.modf(self.get_secs())
        x, secs = divmod(int(t[1]), 60)
        hrs, mins = divmod(x, 60)
        return hrs, mins, secs, t[0]
        
    # Return accurate GPS time of day (hrs <int>, mins <int>, secs<float>)
    def get_t_split(self):
        hrs, mins, secs, frac_secs = self._get_hms()
        return hrs, mins, secs + frac_secs

    # Return a time/date tuple suitable for setting RTC
    def _get_td_split(self):
        d, m, y = self.gps.date
        y += 2000
        hrs, mins, secs, frac_secs = self._get_hms()
        ss = int(255*(1 - frac_secs))
        return y, m, d, week_day(y, m, d), hrs, mins, secs, ss

    def set_rtc(self):
        rtc.datetime(self._get_td_split())

    # Time from GPS: integer μs since Y2K. Call after awaiting PPS: result is
    # time when PPS leading edge occurred so fractional secs discarded.
    def _get_gps_usecs(self):
        d, m, y = self.gps.date
        y += 2000
        hrs, mins, secs, _ = self._get_hms()
        tim = utime.mktime((y, m, d, hrs, mins, secs, week_day(y, m, d) - 1, 0))
        return tim * 1000000

    # Value of RTC time at current instant. Units μs since Y2K. Tests OK.
    def _get_rtc_usecs(self):
        y, m, d, weekday, hrs, mins, secs, subsecs = rtc.datetime()
        tim = 1000000 * utime.mktime((y, m, d, hrs, mins, secs, weekday - 1, 0))
        return tim + ((1000000 * (255 - subsecs)) >> 8)

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
        t = self._get_rtc_usecs()  # Read RTC now
        assert abs(dt) < 10000
        return t - dt

    # Non-realtime calculation of calibration factor. times are in μs
    def _calculate(self, gps_start, gps_end, rtc_start, rtc_end):
        # Duration (μs) between PPS edges
        pps_delta = (gps_end - gps_start)
        # Duration (μs) between PPS edges as measured by RTC and corrected
        rtc_delta = (rtc_end - rtc_start) 
        ppm = (1000000 * (rtc_delta - pps_delta)) / pps_delta  # parts per million
        return int(-ppm/0.954)

    # Measure difference between RTC and GPS rate and return calibration factor
    # Note this blocks for upto 1 sec at intervals. If 3 successive identical
    # results are measured the outcome is considered valid and the coro quits.
    async def getcal(self, minutes=5):
        if minutes < 1:
            raise ValueError('minutes must be >= 1')
        results = [0, 0, 0]  # Last 3 cal results
        idx = 0  # Index into above circular buffer
        nresults = 0  # Count of results
        rtc.calibration(0)  # Clear existing RTC calibration
        self.set_rtc()
        # Wait for PPS, then RTC 1/256 second change. Return the time the RTC
        # would have measured at instant of PPS (μs since Y2K).
        rtc_start = self._await_pps()
        # GPS start time in μs since Y2K: correct at the time of PPS edge.
        gps_start = self._get_gps_usecs()
        # ******** HACK ********
        # This synchronisation phase is necessary because of occasional anomalous
        # readings which result in incorrect start times. If start times are wrong
        # it would take a very long time to converge.
        synchronised = False
        while not synchronised:
            await asyncio.sleep(10)
            rtc_end = self._await_pps()
            gps_end = self._get_gps_usecs()
            cal = self._calculate(gps_start, gps_end, rtc_start, rtc_end)
            if abs(cal) < 2000:
                synchronised = True
            else:
                print('Resync', (gps_end - gps_start) / 1000000, (rtc_end - rtc_start) / 1000000)
                # On 1st pass GPS delta is sometimes exactly 10s and RTC delta is 11s.
                # Subsequently both deltas increase by 11s each pass (which figures).
                rtc_start = rtc_end  # Still getting instances where RTC delta > GPS delta by 1.0015 second
                gps_start = gps_end

        for n in range(minutes):
            for _ in range(6):  # Try every 10s
                await asyncio.sleep(10)
                # Get RTC time at instant of PPS
                rtc_end = self._await_pps()
                gps_end = self._get_gps_usecs()
                cal = self._calculate(gps_start, gps_end, rtc_start, rtc_end)
                print('Run', (gps_end - gps_start) / 1000000, (rtc_end - rtc_start) / 1000000)
                print('Mins {:d} cal factor {:d}'.format(n + 1, cal))
                results[idx] = cal
                idx += 1
                idx %= len(results)
                nresults += 1
                if nresults > 5 and len(set(results)) == 1:
                    return cal  # 3 successive identical results received
        return cal

    # Pause until time/date message received and 1st PPS interrupt has occurred.
    async def ready(self):
        while self.acquired is None:
            await asyncio.sleep(1)

    async def calibrate(self, minutes=5):
        print('Waiting for GPS startup.')
        await self.ready()
        print('Waiting up to {} minutes to acquire calibration factor...'.format(minutes))
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
    gps = as_GPS.AS_GPS(sreader, local_offset=1, fix_cb=lambda *_: red.toggle())
    pps_pin = pyb.Pin('X3', pyb.Pin.IN)
    gps_tim = GPS_Timer(gps, pps_pin)
    await gps_tim.calibrate(minutes)

def test(minutes=5):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_test(minutes))
