# as_tGPS.py Using GPS for precision timing and for calibrating Pyboard RTC
# This is STM-specific: requires pyb module.

# Copyright (c) 2018 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import math
import pyb
import utime
import micropython
import as_GPS

micropython.alloc_emergency_exception_buf(100)

rtc = pyb.RTC()

# Convenience function. Return RTC seconds since midnight as float
def rtc_secs():
    dt = rtc.datetime()
    return 3600*dt[4] + 60*dt[5] + dt[6] + (255 - dt[7])/256

class GPS_Timer():
    def __init__(self, gps, pps_pin, led=None):
        self.gps = gps
        self.led = led
        self.secs = None  # Integer time since midnight at last PPS
        self.acquired = None  # Value of ticks_us at edge of PPS
        self.rtc_set = None  # Data for setting RTC
        loop = asyncio.get_event_loop()
        loop.create_task(self._start(pps_pin))

    async def _start(self, pps_pin):
        await self.gps.data_received(date=True)
        pyb.ExtInt(pps_pin, pyb.ExtInt.IRQ_RISING, pyb.Pin.PULL_NONE, self._isr)

    def _isr(self, _):
        self.acquired = utime.ticks_us()  # Save time of PPS
        if self.rtc_set is not None:
            rtc.datetime(self.rtc_set)
            self.rtc_set = None
        # Time in last NMEA sentence
        t = self.gps.local_time
        # secs is rounded down to an int: exact time of last PPS.
        # This PPS is one second later
        self.secs = 3600*t[0] + 60*t[1] + int(t[2]) + 1
        # Could be an outage here, so PPS arrives many secs after last sentence
        # Is this right? Does PPS continue during outage?
        if self.led is not None:
            self.led.toggle()

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

    # Subsecs register is read-only. So need to set RTC on PPS leading edge.
    # Calculate time of next edge, save the new RTC time, and let ISR update
    # the RTC.
    async def set_rtc(self):
        d, m, y = self.gps.date
        y += 2000
        t0 = self.acquired
        while self.acquired == t0:  # Busy-wait on PPS interrupt
            await asyncio.sleep_ms(0)
        hrs, mins, secs = self.gps.local_time
        secs = int(secs) + 2  # Time of next PPS
        self.rtc_set = [y, m, d, self.gps._week_day(y, m, d), hrs, mins, secs, 0]
#        rtc.datetime((y, m, d, self.gps._week_day(y, m, d), hrs, mins, secs, 0))

    # Time from GPS: integer μs since Y2K. Call after awaiting PPS: result is
    # time when PPS leading edge occurred so fractional secs discarded.
    def _get_gps_usecs(self):
        d, m, y = self.gps.date
        y += 2000
        hrs, mins, secs, _ = self._get_hms()
        tim = utime.mktime((y, m, d, hrs, mins, secs, self.gps._week_day(y, m, d) - 1, 0))
        return tim * 1000000

    # Value of RTC time at current instant. Units μs since Y2K. Tests OK.
    def _get_rtc_usecs(self):
        y, m, d, weekday, hrs, mins, secs, subsecs = rtc.datetime()
        tim = 1000000 * utime.mktime((y, m, d, hrs, mins, secs, weekday - 1, 0))
        return tim + ((1000000 * (255 - subsecs)) >> 8)

    # Return no. of μs RTC leads GPS. Done by comparing times at the instant of
    # PPS leading edge.
    async def delta(self):
        rtc_time = await self._await_pps()  # μs since Y2K at time of latest PPS
        gps_time = self._get_gps_usecs()  # μs since Y2K at previous PPS
        return rtc_time - gps_time + 1000000  # so add 1s

    # Pause until PPS interrupt occurs. Then wait for an RTC subsecond change.
    # Read the RTC time in μs since Y2K and adjust to give the time the RTC
    # (notionally) would have read at the PPS leading edge.
    async def _await_pps(self):
        t0 = self.acquired
        while self.acquired == t0:  # Busy-wait on PPS interrupt
            await asyncio.sleep_ms(0)
        st = rtc.datetime()[7]
        while rtc.datetime()[7] == st:  # Wait for RTC to change (4ms max)
            pass
        dt = utime.ticks_diff(utime.ticks_us(), self.acquired)
        t = self._get_rtc_usecs()  # Read RTC now
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
    # If 3 successive identical results are within 1 digit the outcome is considered
    # valid and the coro quits.
    async def _getcal(self, minutes=5):
        if minutes < 1:
            raise ValueError('minutes must be >= 1')
        results = [0, 0, 0]  # Last 3 cal results
        idx = 0  # Index into above circular buffer
        nresults = 0  # Count of results
        rtc.calibration(0)  # Clear existing RTC calibration
        await self.set_rtc()
        # Wait for PPS, then RTC 1/256 second change. Return the time the RTC
        # would have measured at instant of PPS (μs since Y2K).
        rtc_start = await self._await_pps()
        # GPS start time in μs since Y2K: correct at the time of PPS edge.
        gps_start = self._get_gps_usecs()
        for n in range(minutes):
            for _ in range(6):  # Try every 10s
                await asyncio.sleep(10)
                # Get RTC time at instant of PPS
                rtc_end = await self._await_pps()
                gps_end = self._get_gps_usecs()
                cal = self._calculate(gps_start, gps_end, rtc_start, rtc_end)
                if abs(cal) > 2000:  # Still occasionally occurs
                    rtc_start = rtc_end
                    gps_start = gps_end
                    cal = 0
                    print('Restarting calibration.')
                else:
                    print('Mins {:d} cal factor {:d}'.format(n + 1, cal))
                results[idx] = cal
                idx += 1
                idx %= len(results)
                nresults += 1
                if nresults >= 4 and (abs(max(results) - min(results)) <= 1):
                    return round(sum(results)/len(results))
        return cal

    # Pause until time/date message received and 1st PPS interrupt has occurred.
    async def ready(self):
        while self.acquired is None:
            await asyncio.sleep(1)

    async def calibrate(self, minutes=5):
        print('Waiting for GPS startup.')
        await self.ready()
        print('Waiting up to {} minutes to acquire calibration factor...'.format(minutes))
        cal = await self._getcal(minutes)
        if cal <= 512 and cal >= -511:
            rtc.calibration(cal)
            print('Pyboard RTC is calibrated. Factor is {:d}.'.format(cal))
        else:
            print('Calibration factor {:d} is out of range.'.format(cal))
