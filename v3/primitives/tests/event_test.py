# event_test.py Test WaitAll, WaitAny, ESwwitch, EButton

# Copyright (c) 2022 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# from primitives.tests.event_test import *

import uasyncio as asyncio
from primitives import Delay_ms, WaitAny, ESwitch, WaitAll, EButton
from pyb import Pin

events = [asyncio.Event() for _ in range(4)]

async def set_events(*ev):
    for n in ev:
        await asyncio.sleep(1)
        print("Setting", n)
        events[n].set()

def clear(msg):
    print(msg)
    for e in events:
        e.clear()

async def can(obj, tim):
    await asyncio.sleep(tim)
    print("About to cancel")
    obj.cancel()

async def foo(tsk):
    print("Waiting")
    await tsk

async def wait_test():
    msg = """
\x1b[32m
Expected output:
Setting 0
Tested WaitAny 0
Setting 1
Tested WaitAny 1
Setting 2
Setting 3
Tested WaitAll 2, 3
Setting 0
Setting 3
Tested WaitAny 0, 3
Cancel in 3s
Setting 0
Setting 1
About to cancel
Cancelled.
Waiting for 4s
Timeout
done
\x1b[39m
"""
    print(msg)
    wa = WaitAny((events[0], events[1], WaitAll((events[2], events[3]))))
    asyncio.create_task(set_events(0))
    await wa.wait()
    clear("Tested WaitAny 0")
    asyncio.create_task(set_events(1))
    await wa.wait()
    clear("Tested WaitAny 1")
    asyncio.create_task(set_events(2, 3))
    await wa.wait()
    clear("Tested WaitAll 2, 3")
    wa = WaitAll((WaitAny((events[0], events[1])), WaitAny((events[2], events[3]))))
    asyncio.create_task(set_events(0, 3))
    await wa.wait()
    clear("Tested WaitAny 0, 3")
    task = asyncio.create_task(wa.wait())
    asyncio.create_task(set_events(0, 1))  # Does nothing
    asyncio.create_task(can(task, 3))
    print("Cancel in 3s")
    try:
        await task
    except asyncio.CancelledError:  # TODO why must we trap this?
        print("Cancelled.")
    print("Waiting for 4s")
    try:
        await asyncio.wait_for(wa.wait(), 4)
    except asyncio.TimeoutError:
        print("Timeout")
    print("done")

val = 0
fail = False
pout = None
polarity = 0

async def monitor(evt, v, verbose):
    global val
    while True:
        await evt.wait()
        evt.clear()
        val += v
        verbose and print("Got", hex(v), hex(val))

async def pulse(ms=100):
    pout(1 ^ polarity)
    await asyncio.sleep_ms(ms)
    pout(polarity)

def expect(v, e):
    global fail
    if v == e:
        print("Pass")
    else:
        print(f"Fail: expected {e} got {v}")
        fail = True

async def btest(btn, verbose, supp):
    global val, fail
    val = 0
    events = btn.press, btn.release, btn.double, btn.long
    tasks = []
    for n, evt in enumerate(events):
        tasks.append(asyncio.create_task(monitor(evt, 1 << 3 * n, verbose)))
    await asyncio.sleep(1)
    print("Start short press test")
    await pulse()
    await asyncio.sleep(1)
    verbose and print("Test of short press", hex(val))
    expect(val, 0x09)
    val = 0
    await asyncio.sleep(1)
    print("Start long press test")
    await pulse(2000)
    await asyncio.sleep(4)
    verbose and print("Long press", hex(val))
    exp = 0x208 if supp else 0x209
    expect(val, exp)
    val = 0
    await asyncio.sleep(1)
    print("Start double press test")
    await pulse()
    await asyncio.sleep_ms(100)
    await pulse()
    await asyncio.sleep(4)
    verbose and print("Double press", hex(val))
    exp = 0x48 if supp else 0x52
    expect(val, exp)
    for task in tasks:
        task.cancel()

async def stest(sw, verbose):
    global val, fail
    val = 0
    events = sw.open, sw.close
    tasks = []
    for n, evt in enumerate(events):
        tasks.append(asyncio.create_task(monitor(evt, 1 << 3 * n, verbose)))
    asyncio.create_task(pulse(2000))
    await asyncio.sleep(1)
    expect(val, 0x08)
    await asyncio.sleep(4)  # Wait for any spurious events
    verbose and print("Switch close and open", hex(val))
    expect(val, 0x09)
    for task in tasks:
        task.cancel()

async def switch_test(pol, verbose):
    global val, pout, polarity
    polarity = pol
    pin = Pin('Y1', Pin.IN)
    pout = Pin('Y2', Pin.OUT, value=pol)
    print("Testing EButton.")
    print("suppress == False")
    btn = EButton(pin)
    await btest(btn, verbose, False)
    print("suppress == True")
    btn = EButton(pin, suppress=True)
    await btest(btn, verbose, True)
    print("Testing ESwitch")
    sw = ESwitch(pin, pol)
    await stest(sw, verbose)
    print("Failures occurred.") if fail else print("All tests passed.")

def tests():
    txt="""
    \x1b[32m
    Available tests:
    1. test_switches(polarity=1, verbose=False) Test the ESwitch and Ebutton classe.
    2. test_wait() Test the WaitAny and WaitAll primitives.

    Switch tests assume a Pyboard with a link between Y1 and Y2.
    \x1b[39m
    """
    print(txt)

tests()
def test_switches(polarity=1, verbose=False):
    try:
        asyncio.run(switch_test(polarity, verbose))  # polarity 1/0 is normal (off) electrical state.
    finally:
        asyncio.new_event_loop()
        tests()

def test_wait():
    try:
        asyncio.run(wait_test())
    finally:
        asyncio.new_event_loop()
        tests()
