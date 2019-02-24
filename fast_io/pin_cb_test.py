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

async def killer():
    await asyncio.sleep(20)

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
    loop.run_until_complete(killer())

print('''Link Pyboard pins X1 and X2.

This test uses a timer to toggle pin X1, recording the time of each state change.

The basic test with latency False just demonstrates the callbacks.
The latency test measures the time between the leading edge of X1 output and the
driver detecting the state change. This is in the presence of five competing coros
each of which blocks for 5ms. Latency is on the order of 5ms max under fast_io,
50ms max under official V2.0.

Issue ctrl-D between runs.

test(fast_io=True, latency=False)
args:
fast_io  test fast I/O mechanism.
latency  test latency (delay between X1 and X2 leading edge).
Tests run for 20s.''')
