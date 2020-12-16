# flash.py Heartbeat code for simple uasyncio-based echo server

# Released under the MIT licence
# Copyright (c) Peter Hinch 2019

import uasyncio as asyncio
from sys import platform


async def heartbeat(tms):
    if platform == 'pyboard':  # V1.x or D series
        from pyb import LED
        led = LED(1)
    elif platform == 'esp8266' or platform == 'esp32':
        from machine import Pin
        led = Pin(2, Pin.OUT, value=1)  # Note: Not all ESP8266/ESP32 dev boards have a LED on GPIO2.
    elif platform == 'linux':
        return  # No LED
    else:
        raise OSError('Unsupported platform.')
    while True:
        if platform == 'pyboard':
            led.toggle()
        elif platform == 'esp8266' or platform == 'esp32':
            led(not led())
        await asyncio.sleep_ms(tms)


if __name__ == '__main__':
    try:
        asyncio.run(heartbeat(100))
    except KeyboardInterrupt:
        print('Interrupted')  # This mechanism doesn't work on Unix build.
    finally:
        _ = asyncio.new_event_loop()
