# monitor_pico.py
# Runs on a Raspberry Pico board to receive data from monitor.py

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# UART gets a single ASCII byte defining the pin number and whether
# to increment (uppercase) or decrement (lowercase) the use count.
# Pin goes high if use count > 0 else low.
# incoming numbers are 0..22 which map onto 23 GPIO pins

from machine import UART, Pin, Timer, freq

freq(250_000_000)

# Valid GPIO pins
# GP0,1 are UART 0 so pins are 2..22, 26..27
PIN_NOS = list(range(2,23)) + list(range(26, 28))

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

# native reduced latency to 10μs but killed the hog detector: timer never timed out.
# Also locked up Pico so ctrl-c did not interrupt.
#@micropython.native
def run(period=100, verbose=[], device="uart"):
    global t_ms
    t_ms = period
    for x in verbose:
        pins[x][2] = True
    # Provide for future devices. Must support a blocking read.
    if device == "uart":
        uart = UART(0, 1_000_000)  # rx on GPIO 1
        def read():
            while not uart.any():
                pass
            return ord(uart.read(1))

    while True:
        if x := read():  # Get an initial 0 on UART
            if x == 0x7a:  # Init: program under test has restarted
                for pin in pins:
                    pin[1] = 0
                continue
            if x == 0x40:  # Retrigger hog detector.
                tim.init(period=t_ms, mode=Timer.ONE_SHOT, callback=_cb)
            p = pins[x & 0x1f]  # Key: 0x40 (ord('@')) is pin ID 0
            if x & 0x20:  # Going down
                p[1] -= 1
                if not p[1]:  # Instance count is zero
                    p[0](0)
            else:
                p[0](1)
                p[1] += 1
            if p[2]:
                print(f'ident {i} count {p[1]}')
