# htu_test.py Demo program for portable asynchronous HTU21D driver

# Author: Peter Hinch
# Copyright Peter Hinch 2018 Released under the MIT license

import uasyncio as asyncio
import sys
from machine import Pin, I2C
from .htu21d_mc import HTU21D

if sys.platform == 'pyboard':
    i2c = I2C(1)  # scl=X9 sda=X10
else:
    # Specify pullup: on my ESP32 board pullup resistors are not fitted :-(
    scl_pin = Pin(22, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
    sda_pin = Pin(23, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
    # Standard port
    i2c = I2C(-1, scl=scl_pin, sda=sda_pin)
    # Loboris port (soon this special treatment won't be needed).
    # https://forum.micropython.org/viewtopic.php?f=18&t=3553&start=390
    #i2c = I2C(scl=scl_pin, sda=sda_pin)

htu = HTU21D(i2c, read_delay=2)  # read_delay=2 for test purposes

async def main():
    await htu
    while True:
        fstr = 'Temp {:5.1f} Humidity {:5.1f}'
        print(fstr.format(htu.temperature, htu.humidity))
        await asyncio.sleep(5)

asyncio.run(main())
