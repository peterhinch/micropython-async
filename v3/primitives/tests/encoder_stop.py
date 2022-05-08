# encoder_stop.py Demo of callback which occurs after motion has stopped.

from machine import Pin
import uasyncio as asyncio
from primitives.encoder import Encoder
from primitives.delay_ms import Delay_ms

px = Pin('X1', Pin.IN, Pin.PULL_UP)
py = Pin('X2', Pin.IN, Pin.PULL_UP)

tim = Delay_ms(duration=400)  # High value for test
d = 0

def tcb(pos, delta):  # User callback gets args of encoder cb
    global d
    d = 0
    print(pos, delta)

def cb(pos, delta):  # Encoder callback occurs rapidly
    global d
    tim.trigger()  # Postpone the user callback
    tim.callback(tcb, (pos, d := d + delta))  # and update its args

async def main():
    while True:
        await asyncio.sleep(1)

def test():
    print('Running encoder test. Press ctrl-c to teminate.')
    Encoder.delay = 0  # No need for this delay
    enc = Encoder(px, py, callback=cb)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Interrupted')
    finally:
        asyncio.new_event_loop()

test()
