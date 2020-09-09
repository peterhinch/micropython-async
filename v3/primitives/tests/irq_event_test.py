# irq_event_test.py Test for irq_event class
# Run on Pyboard with link between X1 and X2

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# from primitives.tests.irq_event_test import test
# test()

from machine import Pin
from pyb import LED
import uasyncio as asyncio
import micropython
from primitives.irq_event import IRQ_EVENT

def printexp():
    print('Test expects a Pyboard with X1 and X2 linked. Expected output:')
    print('\x1b[32m')
    print('Flashes red LED and prints numbers 0-19')
    print('\x1b[39m')
    print('Runtime: 20s')

printexp()

micropython.alloc_emergency_exception_buf(100)

driver = Pin(Pin.board.X2, Pin.OUT)
receiver = Pin(Pin.board.X1, Pin.IN)
evt_rx = IRQ_EVENT()

def pin_han(pin):
    evt_rx.set()

receiver.irq(pin_han, Pin.IRQ_FALLING, hard=True)

async def pulse_gen(pin):
    while True:
        await asyncio.sleep_ms(500)
        pin(not pin())

async def red_handler(evt_rx):
    led = LED(1)
    for x in range(20):
        await evt_rx.wait()
        print(x)
        led.toggle()

async def irq_test():
    pg = asyncio.create_task(pulse_gen(driver))
    await red_handler(evt_rx)
    pg.cancel()

def test():
    try:
        asyncio.run(irq_test())
    finally:
        asyncio.new_event_loop()
