# lp_uart.py Demo of using uasyncio to reduce Pyboard power consumption
# Author: Peter Hinch
# Copyright Peter Hinch 2018 Released under the MIT license

# The files rtc_time.py and rtc_time_cfg.py must be on the path.
# Requires a link between X1 and X2.
# Periodically sends a line on UART4 at 9600 baud.
# This is received on UART4 and re-sent on UART1 (pin Y1) at 115200 baud.

import pyb
import rtc_time_cfg
rtc_time_cfg.enabled = True  # Must be done before importing uasyncio

import uasyncio as asyncio
try:
    if asyncio.version[0] != 'fast_io':
        raise AttributeError
except AttributeError:
    raise OSError('This requires fast_io fork of uasyncio.')
from rtc_time import Latency, use_utime

# Stop the test after a period
async def killer(duration):
    await asyncio.sleep(duration)

# Periodically send text through UART
async def sender(uart):
    swriter = asyncio.StreamWriter(uart, {})
    while True:
        await swriter.awrite('Hello uart\n')
        await asyncio.sleep(1.3)

# Each time a message is received echo it on uart 4
async def receiver(uart_in, uart_out):
    sreader = asyncio.StreamReader(uart_in)
    swriter = asyncio.StreamWriter(uart_out, {})
    while True:
        res = await sreader.readline()
        await swriter.awrite(res)

def test(duration):
    if use_utime:  # Not running in low power mode
        pyb.LED(3).on()
    uart2 = pyb.UART(1, 115200)
    uart4 = pyb.UART(4, 9600)
    # Instantiate event loop before using it in Latency class
    loop = asyncio.get_event_loop()
    lp = Latency(50)  # ms
    loop.create_task(sender(uart4))
    loop.create_task(receiver(uart4, uart2))
    loop.run_until_complete(killer(duration))

test(60)
