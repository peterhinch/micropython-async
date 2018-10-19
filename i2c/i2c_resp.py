# i2c_resp.py Test program for asi2c.py
# Tests Responder on a Pyboard.

# The MIT License (MIT)
#
# Copyright (c) 2018 Peter Hinch
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

# scl = X9
# sda = X10
# sync = X11
# ack = Y8 - Y8

import uasyncio as asyncio
from machine import Pin, I2C
import asi2c
import ujson

i2c = I2C(1)
#i2c = I2C(scl=Pin('X9'),sda=Pin('X10'))  # software I2C
syn = Pin('X11')
ack = Pin('Y8')
chan = asi2c.Responder(i2c, syn, ack)

async def receiver():
    sreader = asyncio.StreamReader(chan)
    await chan.ready()
    print('started')
    for _ in range(5):  # Test flow control
        res = await sreader.readline()
        print('Received', ujson.loads(res))
        await asyncio.sleep(4)
    while True:
        res = await sreader.readline()
        print('Received', ujson.loads(res))

async def sender():
    swriter = asyncio.StreamWriter(chan, {})
    txdata = [0, 0]
    while True:
        await swriter.awrite(''.join((ujson.dumps(txdata), '\n')))
        txdata[1] += 1
        await asyncio.sleep_ms(1500)

loop = asyncio.get_event_loop()
loop.create_task(receiver())
loop.create_task(sender())
try:
    loop.run_forever()
finally:
    chan.close()  # for subsequent runs
