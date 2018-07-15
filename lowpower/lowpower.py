# lowpower.py Demo of using uasyncio to reduce Pyboard power consumption
# Author: Peter Hinch
# Copyright Peter Hinch 2018 Released under the MIT license

# The file rtc_time.py must be on the path for this to work at low power.

import pyb
import uasyncio as asyncio
import rtc_time

# Stop the test after a period
async def killer(duration):
    await asyncio.sleep(duration)

# Briefly pulse an LED to save power
async def pulse(led):
    led.on()
    await asyncio.sleep_ms(200)
    led.off()

# Flash an LED forever
async def flash(led, ms):
    while True:
        await pulse(led)
        await asyncio.sleep_ms(ms)

# Periodically send text through UART
async def sender(uart):
    swriter = asyncio.StreamWriter(uart, {})
    while True:
        await swriter.awrite('Hello uart\n')
        await asyncio.sleep(1.3)

# Each time a message is received pulse the LED
async def receiver(uart, led):
    sreader = asyncio.StreamReader(uart)
    while True:
        await sreader.readline()
        await pulse(led)

def test(duration):
    # For lowest power consumption set unused pins as inputs with pullups.
    # Note the 4K7 I2C pullups on X9 X10 Y9 Y10.
    for pin in [p for p in dir(pyb.Pin.board) if p[0] in 'XY']:
        pin_x = pyb.Pin(pin, pyb.Pin.IN, pyb.Pin.PULL_UP)
    if rtc_time.use_utime:  # Not running in low power mode
        pyb.LED(4).on()
    uart = pyb.UART(4, 115200)
    loop = asyncio.get_event_loop()
    loop.create_task(rtc_time.lo_power(100))
    loop.create_task(flash(pyb.LED(1), 4000))
    loop.create_task(sender(uart))
    loop.create_task(receiver(uart, pyb.LED(2)))
    loop.run_until_complete(killer(duration))

test(60)
