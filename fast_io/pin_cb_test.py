# ********* TEST **********

# With fast_io false latency is up to 50.96ms
# With fast_io True we see ~450μs to 5.208ms.

import utime
import pyb
import uasyncio as asyncio
from pin_cb import PinCall

t = 0  # Time of last output transition
max_latency = 0
pinout = pyb.Pin(pyb.Pin.board.X1, pyb.Pin.OUT)

# Timer callback: generate asynchronous pin state changes
def toggle(_):
    global t
    pinout.value(not pinout.value())
    t = utime.ticks_us()

# Callback for basic test
def cb(pin, ud):
    print('Callback', pin.value(), ud)

# Callback for latency test
def cbl(pinin):
    global max_latency
    dt = utime.ticks_diff(utime.ticks_us(), t)
    max_latency = max(max_latency, dt)
    print('Latency {:6d}μs {:6d}μs max'.format(dt, max_latency))

async def dummy():
    while True:
        await asyncio.sleep(0)
        utime.sleep_ms(5)  # Emulate slow processing

def test(fast_io=True, latency=False):
    loop = asyncio.get_event_loop(ioq_len=6 if fast_io else 0)
    pinin = pyb.Pin(pyb.Pin.board.X2, pyb.Pin.IN)
    pyb.Timer(4, freq = 2.1, callback = toggle)
    for _ in range(5):
        loop.create_task(dummy())
    if latency:
        pin_cb = PinCall(pinin, cb_rise = cbl, cbr_args = (pinin,))
    else:
        pincall = PinCall(pinin, cb_rise = cb, cbr_args = (pinin, 'rise'), cb_fall = cb, cbf_args = (pinin, 'fall'))
    loop.run_forever()

print('''Link Pyboard pins X1 and X2.
Issue ctrl-D between runs.
test() args:
fast_io=True  test fast I/O mechanism.
latency=False test latency (delay between X1 and X3 leading edge)''')
