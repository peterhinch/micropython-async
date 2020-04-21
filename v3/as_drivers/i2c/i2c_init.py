# i2c_init.py Test program for asi2c.py. Adapted for uasyncio V3, WBUS DIP28.
# Tests Initiator on a Pyboard

# The MIT License (MIT)
#
# Copyright (c) 2018-2020 Peter Hinch
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

import uasyncio as asyncio
from pyb import I2C  # Only pyb supports slave mode
from machine import Pin
from .asi2c_i import Initiator
import ujson
import os

i2c = I2C(2, mode=I2C.SLAVE)
syn = Pin('Y11')
ack = Pin('X6')
# Reset on Pyboard and ESP8266 is active low. Use 200ms pulse.
rst = (Pin('Y12'), 0, 200)
chan = Initiator(i2c, syn, ack, rst)
if os.uname().machine.split(' ')[0][:4] == 'PYBD':
    Pin.board.EN_3V3.value(1)

async def receiver():
    sreader = asyncio.StreamReader(chan)
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
    await swriter.awrite(''.join((ujson.dumps('this is a test 1'), '\n')))
    await swriter.awrite(''.join((ujson.dumps('this is a test 2'), '\n')))
    await swriter.awrite(''.join((ujson.dumps('this is a test 3'), '\n')))
    while True:
        await swriter.awrite(''.join((ujson.dumps(txdata), '\n')))
        txdata[0] += 1
        await asyncio.sleep_ms(800)

async def test():
    asyncio.create_task(receiver())
    asyncio.create_task(sender())
    while True:
        await chan.ready()
        await asyncio.sleep(10)
        if chan.block_cnt:
            print('Blocking time {:d}μs max. {:d}μs mean.'.format(
                chan.block_max, int(chan.block_sum/chan.block_cnt)))
        print('Reboots: ', chan.nboots)

try:
    asyncio.run(test())
except KeyboardInterrupt:
    print('Interrupted')
finally:
    asyncio.new_event_loop()
    chan.close()  # for subsequent runs
