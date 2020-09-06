# sr_passive.py Test of synchronous comms library. Passive end.

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

# Run on ESP8266
import uasyncio as asyncio
from syncom import SynCom
from machine import Pin, freq
import gc

async def passive_task(chan):
    while True:
        obj = await chan.await_obj()
        if obj is not None:                 # Ignore timeouts
#        print('passive received: ', obj)
            obj[2] += 1                     # modify object and send it back
            chan.send(obj)

async def heartbeat():
    led = Pin(2, Pin.OUT)
    while True:
        await asyncio.sleep_ms(500)
        led(not led())
        gc.collect()

def test():
    freq(160000000)
    dout = Pin(14, Pin.OUT, value = 0)     # Define pins
    ckout = Pin(15, Pin.OUT, value = 0)    # clocks must be initialised to zero.
    din = Pin(13, Pin.IN)
    ckin = Pin(12, Pin.IN)

    channel = SynCom(True, ckin, ckout, din, dout)
    loop = asyncio.get_event_loop()
    loop.create_task(heartbeat())
    loop.create_task(channel.start(passive_task))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ckout(0)

test()
