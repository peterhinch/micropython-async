# adctest.py

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
from machine import ADC
import pyb
from primitives import AADC

async def signal():  # Could use write_timed but this prints values
    dac = pyb.DAC(1, bits=12, buffering=True)
    v = 0
    while True:
        if not v & 0xf:
            print('write', v << 4)  # Make value u16 as per ADC read
        dac.write(v)
        v += 1
        v %= 4096
        await asyncio.sleep_ms(50)

async def adctest():
    asyncio.create_task(signal())
    adc = AADC(ADC(pyb.Pin.board.X1))
    await asyncio.sleep(0)
    adc.sense(normal=False)  # Wait until ADC gets to 5000
    value =  await adc(5000, 10000)
    print('Received', value, adc.read_u16(True))  # Reduce to 12 bits
    adc.sense(normal=True)  # Now print all changes > 2000
    while True:
        value = await adc(2000)  # Trigger if value changes by 2000
        print('Received', value, adc.read_u16(True))

st = '''This test requires a Pyboard with pins X1 and X5 linked.
A sawtooth waveform is applied to the ADC. Initially the test waits
until the ADC value reaches 5000. It then reports whenever the value
changes by 2000.
Issue test() to start.
'''
print(st)

def test():
    try:
        asyncio.run(adctest())
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        asyncio.new_event_loop()
        print()
        print(st)
