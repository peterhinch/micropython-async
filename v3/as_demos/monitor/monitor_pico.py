# monitor_pico.py
# Runs on a Raspberry Pico board to receive data from monitor.py

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# UART gets a single ASCII byte defining the pin number and whether
# to increment (uppercase) or decrement (lowercase) the use count.
# Pin goes high if use count > 0 else low.
# incoming numbers are 0..22 which map onto 23 GPIO pins

from machine import UART, Pin, Timer

# Valid GPIO pins
# GP0,1 are UART 0 so pins are 2..22, 26..27
PIN_NOS = list(range(2,23)) + list(range(26, 28))
uart = UART(0, 1_000_000)  # rx on GP1

pin_t = Pin(28, Pin.OUT)
def _cb(_):
    pin_t(1)
    print('Hog')
    pin_t(0)

tim = Timer()
t_ms = 100
# Index is incoming ID
# contents [Pin, instance_count, verbose]
pins = []
for pin_no in PIN_NOS:
    pins.append([Pin(pin_no, Pin.OUT), 0, False])

def run(period=100, verbose=[]):
    global t_ms
    t_ms = period
    for x in verbose:
        pins[x][2] = True
    while True:
        while not uart.any():
            pass
        x = ord(uart.read(1))
        #print('got', chr(x)) gets CcAa
        if not 0x40 <= x <= 0x7f:  # Get an initial 0
            continue
        if x == 0x40:
            tim.init(period=t_ms, mode=Timer.ONE_SHOT, callback=_cb)
        i = x & 0x1f  # Key: 0x40 (ord('@')) is pin ID 0
        d = -1 if x & 0x20 else 1
        pins[i][1] += d
        if pins[i][1]:  # Count > 0 turn pin on
            pins[i][0](1)
        else:
            pins[i][0](0)
        if pins[i][2]:
            print(f'ident {i} count {pins[i][1]}')
