# monitor.py
# Monitor an asynchronous program by sending single bytes down an interface.

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
from machine import UART, SPI, Pin
from time import sleep_us
from sys import exit

# Quit with an error message rather than throw.
def _quit(s):
    print("Monitor " + s)
    exit(0)


_write = lambda _: _quit("must run set_device")
_ifrst = lambda: None  # Reset interface. If UART do nothing.

# For UART pass initialised UART. Baudrate must be 1_000_000.
# For SPI pass initialised instance SPI. Can be any baudrate, but
# must be default in other respects.
def set_device(dev, cspin=None):
    global _write
    global _ifrst
    if isinstance(dev, UART) and cspin is None:  # UART
        _write = dev.write
    elif isinstance(dev, SPI) and isinstance(cspin, Pin):
        cspin(1)

        def spiwrite(data):
            cspin(0)
            dev.write(data)
            cspin(1)

        _write = spiwrite

        def clear_sm():  # Set Pico SM to its initial state
            cspin(1)
            dev.write(b"\0")  # SM is now waiting for CS low.

        _ifrst = clear_sm
    else:
        _quit("set_device: invalid args.")


# Justification for validation even when decorating a method
# /mnt/qnap2/data/Projects/Python/AssortedTechniques/decorators
_available = set(range(0, 22))  # Valid idents are 0..21
_reserved = set()  # Idents reserved for synchronous monitoring


def _validate(ident, num=1):
    if ident >= 0 and ident + num < 22:
        try:
            for x in range(ident, ident + num):
                _available.remove(x)
        except KeyError:
            _quit("error - ident {:02d} already allocated.".format(x))
    else:
        _quit("error - ident {:02d} out of range.".format(ident))


# Reserve ID's to be used for synchronous monitoring
def reserve(*ids):
    for ident in ids:
        _validate(ident)
        _reserved.add(ident)


# Check whether a synchronous ident was reserved
def _check(ident):
    if ident not in _reserved:
        _quit("error: synchronous ident {:02d} was not reserved.".format(ident))


# asynchronous monitor
def asyn(n, max_instances=1, verbose=True):
    def decorator(coro):
        _validate(n, max_instances)
        instance = 0

        async def wrapped_coro(*args, **kwargs):
            nonlocal instance
            d = 0x40 + n + min(instance, max_instances - 1)
            v = int.to_bytes(d, 1, "big")
            instance += 1
            if verbose and instance > max_instances:  # Warning only.
                print("Monitor ident: {:02d} instances: {}.".format(n, instance))
            _write(v)
            try:
                res = await coro(*args, **kwargs)
            except asyncio.CancelledError:
                raise  # Other exceptions produce traceback.
            finally:
                d |= 0x20
                v = int.to_bytes(d, 1, "big")
                _write(v)
                instance -= 1
            return res

        return wrapped_coro

    return decorator


# If SPI, clears the state machine in case prior test resulted in the DUT
# crashing. It does this by sending a byte with CS\ False (high).
def init():
    _ifrst()  # Reset interface. Does nothing if UART.
    _write(b"z")  # Clear Pico's instance counters etc.


# Optionally run this to show up periods of blocking behaviour
async def hog_detect(s=(b"\x40", b"\x60")):
    while True:
        for v in s:
            _write(v)
            await asyncio.sleep_ms(0)


# Monitor a synchronous function definition
def sync(n):
    def decorator(func):
        _validate(n)
        vstart = int.to_bytes(0x40 + n, 1, "big")
        vend = int.to_bytes(0x60 + n, 1, "big")

        def wrapped_func(*args, **kwargs):
            _write(vstart)
            res = func(*args, **kwargs)
            _write(vend)
            return res

        return wrapped_func

    return decorator


# Runtime monitoring: can't validate because code may be looping.
# Monitor a synchronous function call
class mon_call:
    def __init__(self, n):
        _check(n)
        self.vstart = int.to_bytes(0x40 + n, 1, "big")
        self.vend = int.to_bytes(0x60 + n, 1, "big")

    def __enter__(self):
        _write(self.vstart)
        return self

    def __exit__(self, type, value, traceback):
        _write(self.vend)
        return False  # Don't silence exceptions


# Cause pico ident n to produce a brief (~80μs) pulse
def trigger(n):
    _check(n)
    _write(int.to_bytes(0x40 + n, 1, "big"))
    sleep_us(20)
    _write(int.to_bytes(0x60 + n, 1, "big"))
