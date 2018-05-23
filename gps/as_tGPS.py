# as_tGPS.py Using GPS for precision timing and for calibrating Pyboard RTC
# This is STM-specific: requires pyb module.

# Copyright (c) 2018 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
import pyb
import utime
import micropython
import gc
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
        self._rtc_set = False  # Set RTC flag
        loop = asyncio.get_event_loop()
        loop.create_task(self._start(pps_pin))

    async def _start(self, pps_pin):
        await self.gps.data_received(date=True)
        pyb.ExtInt(pps_pin, pyb.ExtInt.IRQ_RISING, pyb.Pin.PULL_NONE, self._isr)

    def _isr(self, _):
        acquired = utime.ticks_us()  # Save time of PPS
        # Time in last NMEA sentence was time of last PPS.
        # Reduce to secs since midnight local time.
        secs = (self.gps.epoch_time + int(3600*self.gps.local_offset)) % 86400
        # This PPS is one second later
        secs += 1
        if secs >= 86400:  # Next PPS will deal with rollover
            return
        self.secs = secs
        self.acquired = acquired
        if self._rtc_set:
            # Time in last NMEA sentence. Earlier test ensures no rollover.
            self.gps._rtcbuf[6] = secs % 60
            rtc.datetime(self.gps._rtcbuf)
            self._rtc_set = False
        # Could be an outage here, so PPS arrives many secs after last sentence
        # Is this right? Does PPS continue during outage?
        if self.led is not None:
            self.led.toggle()

    # Subsecs register is read-only. So need to set RTC on PPS leading edge.
    # Set flag and let ISR set the RTC. Pause until done.
    async def set_rtc(self):
        self._rtc_set = True
        while self._rtc_set:
            await asyncio.sleep_ms(250)

    # Value of RTC time at current instant. This is a notional arbitrary
    # precision integer in μs since Y2K. Notional because RTC is set to
    # local time.
    def _get_rtc_usecs(self):
        y, m, d, weekday, hrs, mins, secs, subsecs = rtc.datetime()
        tim = 1000000 * utime.mktime((y, m, d, hrs, mins, secs, weekday - 1, 0))
        return tim + ((1000000 * (255 - subsecs)) >> 8)

    # Return no. of μs RTC leads GPS. Done by comparing times at the instant of
    # PPS leading edge.
    async def delta(self):
        rtc_time, gps_time = await self._await_pps()  # μs since Y2K at time of latest PPS
        return rtc_time - gps_time

    # Pause until PPS interrupt occurs. Then wait for an RTC subsecond change.
    # Read the RTC time in μs since Y2K and adjust to give the time the RTC
    # (notionally) would have read at the PPS leading edge.
    async def _await_pps(self):
        t0 = self.acquired
        while self.acquired == t0:  # Busy-wait on PPS interrupt
            await asyncio.sleep_ms(0)  # Interrupts here should be OK as ISR stored acquisition time
        gc.collect()
        # DISABLING INTS INCREASES UNCERTAINTY. Interferes with ticks_us (proved by test).
#        istate = pyb.disable_irq()  # But want to accurately time RTC change
        st = rtc.datetime()[7]
        while rtc.datetime()[7] == st:  # Wait for RTC to change (4ms max)
            pass
        dt = utime.ticks_diff(utime.ticks_us(), self.acquired)
        trtc = self._get_rtc_usecs() - dt # Read RTC now and adjust for PPS edge
        tgps = 1000000 * (self.gps.epoch_time + 3600*self.gps.local_offset + 1)
#        pyb.enable_irq(istate)  # Have critical timings now
        return trtc, tgps

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
        # would have measured at instant of PPS (notional μs since Y2K). Also
        # GPS time at the same instant.
        rtc_start, gps_start = await self._await_pps()
        for n in range(minutes):
            for _ in range(6):  # Try every 10s
                await asyncio.sleep(10)
                # Get RTC time at instant of PPS
                rtc_end, gps_end = await self._await_pps()
                cal = self._calculate(gps_start, gps_end, rtc_start, rtc_end)
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

    # User interface functions: accurate GPS time.
    # Return GPS time in ms since midnight (small int on 32 bit h/w).
    # No allocation.
    def get_ms(self):
        state = pyb.disable_irq()
        t = self.secs
        acquired = self.acquired
        pyb.enable_irq(state)
        return 1000*t + utime.ticks_diff(utime.ticks_us(), acquired) // 1000

    # Return accurate GPS time of day (hrs: int, mins: int, secs: int, μs: int)
    # The ISR can skip an update of .secs if a day rollover would occur. Next
    # RMC handles this, so subsequent ISR will see hms = 0, 0, 1 and a value of
    # .acquired > 1000000.
    def get_t_split(self):
        secs, acquired = self.secs, self.acquired  # Single LOC is not interruptable
        x, secs = divmod(secs, 60)
        hrs, mins = divmod(x, 60)
        dt = utime.ticks_diff(utime.ticks_us(), acquired)  # μs to time now
        ds, us = divmod(dt, 1000000)
        # If dt > 1e6 can add to secs without risk of rollover: see above.
        return hrs, mins, secs + ds, us
