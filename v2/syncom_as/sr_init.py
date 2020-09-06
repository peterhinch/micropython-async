# sr_init.py Test of synchronous comms library. Initiator end.

# The MIT License (MIT)
#
# Copyright (c) 2016 Peter Hinch
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Run on Pyboard
from machine import Pin, Signal
from pyb import LED
import uasyncio as asyncio
from utime import ticks_ms, ticks_diff
from syncom import SynCom, SynComError


async def initiator_task(channel):
    while True:
        so = ['test', 0, 0]
        for x in range(4):          # Test full duplex by sending 4 in succession
            so[1] = x
            channel.send(so)
            await asyncio.sleep_ms(0)
        while True:                 # Receive the four responses
            si = await channel.await_obj()  # Deal with queue
            if si is None:
                print('Timeout: restarting.')
                return
            print('initiator received', si)
            if si[1] == 3:          # received last one
                break
        while True:                 # At 2 sec intervals send an object and get response
            await asyncio.sleep(2)
            print('sending', so)
            channel.send(so)
            tim = ticks_ms()
            so = await channel.await_obj()  # wait for response
            duration = ticks_diff(ticks_ms(), tim)
            if so is None:
                print('Timeout: restarting.')
                return
            print('initiator received', so, 'timing', duration)

async def heartbeat():
    led = LED(1)
    while True:
        await asyncio.sleep_ms(500)
        led.toggle()

def test():
    dout = Pin(Pin.board.Y5, Pin.OUT_PP, value = 0)   # Define pins
    ckout = Pin(Pin.board.Y6, Pin.OUT_PP, value = 0)  # Don't assert clock until data is set
    din = Pin(Pin.board.Y7, Pin.IN)
    ckin = Pin(Pin.board.Y8, Pin.IN)
    reset = Pin(Pin.board.Y4, Pin.OPEN_DRAIN)
    sig_reset = Signal(reset, invert = True)

    channel = SynCom(False, ckin, ckout, din, dout, sig_reset, 10000)

    loop = asyncio.get_event_loop()
    loop.create_task(heartbeat())
    loop.create_task(channel.start(initiator_task))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ckout.value(0)

test()
