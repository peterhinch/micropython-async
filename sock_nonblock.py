# sock_nonblock.py Illustration of the type of code required to use nonblocking
# sockets. It is not a working demo and probably has silly errors.
# It is intended as an outline of requirements and also to illustrate some of the
# nasty hacks required on current builds of ESP32 firmware. Platform detection is
# done at runtime.
# If running on ESP8266 these hacks can be eliminated.
# Working implementations may be found in the asynchronous MQTT library.
# https://github.com/peterhinch/micropython-mqtt

# Author: Peter Hinch
# Copyright Peter Hinch 2018 Released under the MIT license

import usocket as socket
import network
import machine
import sys
from micropython import const
from uerrno import EINPROGRESS, ETIMEDOUT
from utime import ticks_ms, ticks_diff, sleep_ms

ESP32 = sys.platform == 'esp32'

BUSY_ERRORS = [EINPROGRESS, ETIMEDOUT]

# ESP32. It is not enough to regularly yield to RTOS with machine.idle(). There are
# two cases where an explicit sleep() is required. Where data has been written to the
# socket and a response is awaited, a timeout may occur without a >= 20ms sleep.
# Secondly during WiFi connection sleeps are required to prevent hangs.
if ESP32:
    # https://forum.micropython.org/viewtopic.php?f=16&t=3608&p=20942#p20942
    BUSY_ERRORS += [118, 119]  # Add in weird ESP32 errors
    # 20ms seems about the minimum before we miss data read from a socket.
    def esp32_pause():  # https://github.com/micropython/micropython-esp32/issues/167
        sleep_ms(20)  # This is horrible.
else:
    esp32_pause = lambda *_ : None  # Do nothing on sane platforms

# How long to delay between polls. Too long affects throughput, too short can
# starve other coroutines.
_SOCKET_POLL_DELAY = const(5)  # ms
_RESPONSE_TIME = const(30000)  # ms. max server latency before timeout

class FOO:
    def __init__(self, server, port):
        # On ESP32 need to submit WiFi credentials
        self._sta_if = network.WLAN(network.STA_IF)
        self._sta_if.active(True)
        # Note that the following blocks, potentially for seconds, owing to DNS lookup
        self._addr = socket.getaddrinfo(server, port)[0][-1]
        self._sock = socket.socket()
        self._sock.setblocking(False)
        try:
            self._sock.connect(addr)
        except OSError as e:
            if e.args[0] not in BUSY_ERRORS:
                raise
        if ESP32:  # Revolting kludge :-(
            loop = asyncio.get_event_loop()
            loop.create_task(self._idle_task())

    def _timeout(self, t):
        return ticks_diff(ticks_ms(), t) > _RESPONSE_TIME

    # Read and return n bytes. Raise OSError on timeout ( caught by superclass).
    async def _as_read(self, n):
        sock = self._sock
        data = b''
        t = ticks_ms()
        while len(data) < n:
            esp32_pause()  # Necessary on ESP32 or we can time out.
            if self._timeout(t) or not self._sta_if.isconnected():
                raise OSError(-1)
            try:
                msg = sock.read(n - len(data))
            except OSError as e:  # ESP32 issues weird 119 errors here
                msg = None
                if e.args[0] not in BUSY_ERRORS:
                    raise
            if msg == b'':  # Connection closed by host (?)
                raise OSError(-1)
            if msg is not None:  # data received
                data = b''.join((data, msg))
                t = ticks_ms()  # reset timeout
            await asyncio.sleep_ms(_SOCKET_POLL_DELAY)
        return data

    # Write a buffer
    async def _as_write(self, bytes_wr):
        sock = self._sock
        t = ticks_ms()
        while bytes_wr:
            if self._timeout(t) or not self._sta_if.isconnected():
                raise OSError(-1)
            try:
                n = sock.write(bytes_wr)
            except OSError as e:  # ESP32 issues weird 119 errors here
                n = 0
                if e.args[0] not in BUSY_ERRORS:
                    raise
            if n:  # Bytes still to write
                t = ticks_ms()  # Something was written: reset t/o
                bytes_wr = bytes_wr[n:]
            esp32_pause()  # Precaution. How to prove whether it's necessary?
            await asyncio.sleep_ms(_SOCKET_POLL_DELAY)

    # ESP32 kludge :-(
    async def _idle_task(self):
        while True:
            await asyncio.sleep_ms(10)
            machine.idle()  # Yield to underlying RTOS
