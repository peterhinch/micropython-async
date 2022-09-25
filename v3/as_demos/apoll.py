# Demonstration of a device driver using a coroutine to poll a device.
# Runs on Pyboard: displays results from the onboard accelerometer.
# Uses crude filtering to discard noisy data.

# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license

import uasyncio as asyncio
import pyb
import utime as time

class Accelerometer(object):
    threshold_squared = 16
    def __init__(self, accelhw, timeout):
        self.accelhw = accelhw
        self.timeout = timeout
        self.last_change = time.ticks_ms()
        self.coords = [accelhw.x(), accelhw.y(), accelhw.z()]

    def dsquared(self, xyz):            # Return the square of the distance between this and a passed 
        return sum(map(lambda p, q : (p-q)**2, self.coords, xyz)) # acceleration vector

    def poll(self):                     # Device is noisy. Only update if change exceeds a threshold
        xyz = [self.accelhw.x(), self.accelhw.y(), self.accelhw.z()]
        if self.dsquared(xyz) > Accelerometer.threshold_squared:
            self.coords = xyz
            self.last_change = time.ticks_ms()
            return 0
        return time.ticks_diff(time.ticks_ms(), self.last_change)

    def vector(self):
        return self.coords

    def timed_out(self):                # Time since last change or last timeout report
        if time.ticks_diff(time.ticks_ms(), self.last_change) > self.timeout:
            self.last_change = time.ticks_ms()
            return True
        return False

async def accel_coro(timeout=2000):
    accelhw = pyb.Accel()               # Instantiate accelerometer hardware
    await asyncio.sleep_ms(30)          # Allow it to settle
    accel = Accelerometer(accelhw, timeout)
    while True:
        result = accel.poll()
        if result == 0:                 # Value has changed
            x, y, z = accel.vector()
            print("Value x:{:3d} y:{:3d} z:{:3d}".format(x, y, z))
        elif accel.timed_out():         # Report every 2 secs
            print("Timeout waiting for accelerometer change")
        await asyncio.sleep_ms(100)     # Poll every 100ms


async def main(delay):
    print('Testing accelerometer for {} secs. Move the Pyboard!'.format(delay))
    print('Test runs for {}s.'.format(delay))
    asyncio.create_task(accel_coro())
    await asyncio.sleep(delay)
    print('Test complete!')

asyncio.run(main(20))
