# mqtt_log.py Demo/test program for MicroPython asyncio low power operation
# Author: Peter Hinch
# Copyright Peter Hinch 2019 Released under the MIT license

# MQTT Demo publishes an incremental count and the RTC time periodically.
# On my SF_2W board consumption while paused was 170μA.

# Test reception e.g. with:
# mosquitto_sub -h 192.168.0.10 -t result

import rtc_time_cfg
rtc_time_cfg.enabled = True

from pyb import LED, RTC
from umqtt.simple import MQTTClient
import network
import ujson
from local import SERVER, SSID, PW  # Local configuration: change this file

import uasyncio as asyncio
try:
    if asyncio.version[0] != 'fast_io':
        raise AttributeError
except AttributeError:
    raise OSError('This requires fast_io fork of uasyncio.')
from rtc_time import Latency

def publish(s):
    c = MQTTClient('umqtt_client', SERVER)
    c.connect()
    c.publish(b'result', s.encode('UTF8'))
    c.disconnect()

async def main(loop):
    rtc = RTC()
    red = LED(1)
    red.on()
    grn = LED(2)
    sta_if = network.WLAN()
    sta_if.active(True)
    sta_if.connect(SSID, PW)
    while sta_if.status() in (1, 2):  # https://github.com/micropython/micropython/issues/4682
        await asyncio.sleep(1)
        grn.toggle()
    if sta_if.isconnected():
        red.off()
        grn.on()
        await asyncio.sleep(1)  # 1s of green == success.
        grn.off()  # Conserve power
        Latency(2000)
        count = 0
        while True:
            print('Publish')
            publish(ujson.dumps([count, rtc.datetime()]))
            count += 1
            print('Wait 2 mins')
            await asyncio.sleep(120)  # 2 mins
    else:  # Fail to connect
        red.on()
        grn.off()

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))
