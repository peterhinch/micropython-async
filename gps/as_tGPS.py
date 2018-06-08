# as_tGPS.py Using GPS for precision timing and for calibrating Pyboard RTC
# This is STM-specific: requires pyb module.
# Hence not as RAM-critical as as_GPS

# Copyright (c) 2018 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file
# TODO Test machine version. Replace LED with callback. Update tests and doc.

import uasyncio as asyncio
import machine
try:
    import pyb
    on_pyboard = True
    rtc = pyb.RTC()
except ImportError:
    on_pyboard = False
import utime
import micropython
import gc
import as_GPS
import as_rwGPS

micropython.alloc_emergency_exception_buf(100)

# Convenience function. Return RTC seconds since midnight as float
def rtc_secs():
    if not on_pyboard:
        raise OSError('Only available on STM targets.')
    dt = rtc.datetime()
    return 3600*dt[4] + 60*dt[5] + dt[6] + (255 - dt[7])/256

# Constructor for GPS_Timer class
def gps_ro_t_init(self, sreader, pps_pin, local_offset=0,
                  fix_cb=lambda *_ : None, cb_mask=as_GPS.RMC, fix_cb_args=(),
                  pps_cb=lambda *_ : None, pps_cb_args=()):
    as_GPS.AS_GPS.__init__(self, sreader, local_offset, fix_cb, cb_mask, fix_cb_args)
    self.setup(pps_pin, pps_cb, pps_cb_args)

# Constructor for GPS_RWTimer class
def gps_rw_t_init(self, sreader, swriter, pps_pin, local_offset=0,
                  fix_cb=lambda *_ : None, cb_mask=as_GPS.RMC, fix_cb_args=(),
                  msg_cb=lambda *_ : None, msg_cb_args=(),
                  pps_cb=lambda *_ : None, pps_cb_args=()):
    as_rwGPS.GPS.__init__(self, sreader, swriter, local_offset, fix_cb, cb_mask, fix_cb_args,
                 msg_cb, msg_cb_args)
    self.setup(pps_pin, pps_cb, pps_cb_args)

class GPS_Tbase():
    def setup(self, pps_pin, pps_cb, pps_cb_args):
        self._pps_pin = pps_pin
        self._pps_cb = pps_cb
        self._pps_cb_args = pps_cb_args
        self.msecs = None  # Integer time in ms since midnight at last PPS
        self.t_ms = 0  # ms since midnight
        self.acquired = None  # Value of ticks_us at edge of PPS
        self._rtc_set = False  # Set RTC flag
        self._rtcbuf = [0]*8  # Buffer for RTC setting
        self._time = [0]*4  # get_t_split() time buffer.
        loop = asyncio.get_event_loop()
        loop.create_task(self._start())

    async def _start(self):
        await self.data_received(date=True)
        self._pps_pin.irq(self._isr, trigger = machine.Pin.IRQ_RISING)

    def close(self):
        self._pps_pin.irq(None)

    # If update rate > 1Hz, when PPS edge occurs the last RMC message will have
    # a nonzero ms value. Need to set RTC to 1 sec after the last 1 second boundary
    def _isr(self, _):
        acquired = utime.ticks_us()  # Save time of PPS
        # Time in last NMEA sentence was time of last PPS.
        # Reduce to integer secs since midnight local time.
        isecs = (self.epoch_time + int(3600*self.local_offset)) % 86400
        # ms since midnight (28 bits). Add in any ms in RMC data
        msecs = isecs * 1000 + self.msecs
        # This PPS is presumed to be one update later
        msecs += self._update_ms
        if msecs >= 86400000:  # Next PPS will deal with rollover
            return
        if self.t_ms == msecs:  # No RMC message has arrived: nothing to do
            return
        self.t_ms = msecs  # Current time in ms past midnight
        self.acquired = acquired
        # Set RTC if required and if last RMC indicated a 1 second boundary
        if self._rtc_set:
            # Time as int(seconds) in last NMEA sentence. Earlier test ensures
            # no rollover when we add 1.
            self._rtcbuf[6] = (isecs + 1) % 60
            rtc.datetime(self._rtcbuf)
            self._rtc_set = False
        # Could be an outage here, so PPS arrives many secs after last sentence
        # Is this right? Does PPS continue during outage?
        self._pps_cb(self, *self._pps_cb_args)

    # Called when base class updates the epoch_time.
    # Need local time for setting Pyboard RTC in interrupt context
    def _dtset(self, wday):
        t = self.epoch_time + int(3600 * self.local_offset)
        y, m, d, hrs, mins, secs, *_ = self._localtime(t)
        self._rtcbuf[0] = y
        self._rtcbuf[1] = m
        self._rtcbuf[2] = d
        self._rtcbuf[3] = wday
        self._rtcbuf[4] = hrs
        self._rtcbuf[5] = mins
        self._rtcbuf[6] = secs

    # Subsecs register is read-only. So need to set RTC on PPS leading edge.
    # Set flag and let ISR set the RTC. Pause until done.
    async def set_rtc(self):
        if not on_pyboard:
            raise OSError('Only available on STM targets.')
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
        if not on_pyboard:
            raise OSError('Only available on STM targets.')
        rtc_time, gps_time = await self._await_pps()  # μs since Y2K at time of latest PPS
        return rtc_time - gps_time

    # Pause until PPS interrupt occurs. Then wait for an RTC subsecond change.
    # Read the RTC time in μs since Y2K and adjust to give the time the RTC
    # (notionally) would have read at the PPS leading edge.
    async def _await_pps(self):
        t0 = self.acquired
        while self.acquired == t0:  # Busy-wait on PPS interrupt: not time-critical
            await asyncio.sleep_ms(0)  # because acquisition time stored in ISR.
        gc.collect()  # Time-critical code follows
        st = rtc.datetime()[7]
        while rtc.datetime()[7] == st:  # Wait for RTC to change (4ms max)
            pass
        dt = utime.ticks_diff(utime.ticks_us(), self.acquired)
        trtc = self._get_rtc_usecs() - dt # Read RTC now and adjust for PPS edge
        tgps = 1000000 * (self.epoch_time + 3600*self.local_offset + 1)
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
        if not on_pyboard:
            raise OSError('Only available on STM targets.')
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
        state = machine.disable_irq()
        t = self.t_ms
        acquired = self.acquired
        machine.enable_irq(state)
        return t + utime.ticks_diff(utime.ticks_us(), acquired) // 1000

    # Return accurate GPS time of day (hrs: int, mins: int, secs: int, μs: int)
    # The ISR can skip an update of .secs if a day rollover would occur. Next
    # RMC handles this, so if updates are at 1s intervals the subsequent ISR
    # will see hms = 0, 0, 1 and a value of .acquired > 1000000.
    # Even at the slowest update rate of 10s this can't overflow into minutes.
    def get_t_split(self):
        state = machine.disable_irq()
        t = self.t_ms
        acquired = self.acquired
        machine.enable_irq(state)
        isecs, ims = divmod(t, 1000)  # Get integer secs and ms
        x, secs = divmod(isecs, 60)
        hrs, mins = divmod(x, 60)
        dt = utime.ticks_diff(utime.ticks_us(), acquired)  # μs to time now
        ds, us = divmod(dt, 1000000)
        # If dt > 1e6 can add to secs without risk of rollover: see above.
        self._time[0] = hrs
        self._time[1] = mins
        self._time[2] = secs + ds
        self._time[3] = us + ims*1000
        return self._time

GPS_Timer = type('GPS_Timer', (GPS_Tbase, as_GPS.AS_GPS), {'__init__': gps_ro_t_init})
GPS_RWTimer = type('GPS_RWTimer', (GPS_Tbase, as_rwGPS.GPS), {'__init__': gps_rw_t_init})
