# monitor_pico.py
# Runs on a Raspberry Pico board to receive data from monitor.py

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Device gets a single ASCII byte defining the pin number and whether
# to increment (uppercase) or decrement (lowercase) the use count.
# Pin goes high if use count > 0 else low.
# incoming numbers are 0..21 which map onto 22 GPIO pins

import rp2
from machine import UART, Pin, Timer, freq

freq(250_000_000)

# ****** SPI support ******
@rp2.asm_pio(autopush=True, in_shiftdir=rp2.PIO.SHIFT_LEFT, push_thresh=8)
def spi_in():
    label("escape")
    set(x, 0)
    mov(isr, x)  # Zero after DUT crash
    wrap_target()
    wait(1, pins, 2)  # CS/ False
    wait(0, pins, 2)  # CS/ True
    set(x, 7)
    label("bit")
    wait(0, pins, 1)
    wait(1, pins, 1)
    in_(pins, 1)
    jmp(pin, "escape")  # DUT crashed. On restart it sends a char with CS high.
    jmp(x_dec, "bit")  # Post decrement
    wrap()


class PIOSPI:

    def __init__(self):
        self._sm = rp2.StateMachine(0, spi_in,
                                    in_shiftdir=rp2.PIO.SHIFT_LEFT,
                                    push_thresh=8, in_base=Pin(0),
                                    jmp_pin=Pin(2, Pin.IN, Pin.PULL_UP))
        self._sm.active(1)

    # Blocking read of 1 char. Returns ord(ch). If DUT crashes, worst case
    # is where CS is left low. SM will hang until user restarts. On restart
    # the app
    def read(self):
        return self._sm.get() & 0xff

# ****** Define pins ******

# Valid GPIO pins
# GPIO 0,1,2 are for interface so pins are 3..22, 26..27
PIN_NOS = list(range(3, 23)) + list(range(26, 28))

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

# ****** Monitor ******
# native reduced latency to 10μs but killed the hog detector: timer never timed out.
# Also locked up Pico so ctrl-c did not interrupt.
#@micropython.native
def run(period=100, verbose=(), device="uart", vb=True):
    global t_ms
    t_ms = period
    for x in verbose:
        pins[x][2] = True
    # A device must support a blocking read.
    if device == "uart":
        uart = UART(0, 1_000_000)  # rx on GPIO 1
        def read():
            while not uart.any():  # Prevent UART timeouts
                pass
            return ord(uart.read(1))
    elif device == "spi":
        pio = PIOSPI()
        def read():
            return pio.read()
    else:
        raise ValueError("Unsupported device:", device)

    vb and print('Awaiting communication')
    while True:
        if x := read():  # Get an initial 0 on UART
            if x == 0x7a:  # Init: program under test has restarted
                vb and print('Got communication.')
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
