# htu21d_mc.py Portable, asynchronous micropython driver for HTU21D temp/humidity I2C sensor
# https://www.sparkfun.com/products/12064 I2C   3.3v
# https://raw.githubusercontent.com/randymxj/Adafruit-Raspberry-Pi-Python-Code/master/Adafruit_HTU21D/Adafruit_HTU21D.py
# Based on https://github.com/manitou48/pyboard/blob/master/htu21d.py

# Author: Peter Hinch
# Copyright Peter Hinch 2018-2020 Released under the MIT license

import machine
import ustruct
import uasyncio as asyncio
from micropython import const

_ADDRESS = const(0x40)  # HTU21D Address
_PAUSE_MS = const(60)  # HTU21D acquisition delay
_READ_USER_REG = const(0xE7)

# CRC8 calculation notes. See https://github.com/sparkfun/HTU21D_Breakout
# Reads 3 temperature/humidity bytes from the sensor
# value[0], value[1] = Raw temp/hum data, value[2] = CRC
# Polynomial = 0x0131 = x^8 + x^5 + x^4 + 1

class HTU21D:
    START_TEMP_MEASURE = b'\xF3'  # Commands
    START_HUMD_MEASURE = b'\xF5'

    def __init__(self, i2c, read_delay=10):
        self.i2c = i2c
        if _ADDRESS not in self.i2c.scan():
            raise OSError('No HTU21D device found.')
        self.temperature = None
        self.humidity = None
        asyncio.create_task(self._run(read_delay))

    async def _run(self, read_delay):
        while True:
            raw_temp = await self._get_data(self.START_TEMP_MEASURE)
            self.temperature = -46.85 + (175.72 * raw_temp / 65536)  # Calculate temp
            raw_rh = await self._get_data(self.START_HUMD_MEASURE)
            self.humidity = -6 + (125.0 * raw_rh / 65536)  # Calculate RH
            await asyncio.sleep(read_delay)

    def __iter__(self):  # Await 1st reading
        while self.humidity is None:
            yield from asyncio.sleep(0)

    async def _get_data(self, cmd, divisor=0x131 << 15, bit=1 << 23):
        self.i2c.writeto(_ADDRESS, cmd)  # Start reading
        await asyncio.sleep_ms(_PAUSE_MS)  # Wait for device
        value = self.i2c.readfrom(_ADDRESS, 3)  # Read result, check CRC8
        data, crc = ustruct.unpack('>HB', value)
        remainder = (data << 8) | crc
        while bit > 128:
            if(remainder & bit):
                remainder ^= divisor
            divisor >>= 1
            bit >>= 1
        if remainder:
            raise OSError('HTU21D CRC Fail')
        return data & 0xFFFC  # Clear the status bits

    def user_register(self):  # Read the user register byte (should be 2)
        return self.i2c.readfrom_mem(_ADDRESS, _READ_USER_REG, 1)[0]
