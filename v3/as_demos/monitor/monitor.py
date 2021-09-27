# monitor.py
# Monitor an asynchronous program by sending single bytes down an interface.

# Copyright (c) 2021 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
from machine import UART, SPI, Pin

_write = lambda _ : print('Must run set_device')
_dummy = lambda : None  # If UART do nothing.

# For UART pass initialised UART. Baudrate must be 1_000_000.
# For SPI pass initialised instance SPI. Can be any baudrate, but
# must be default in other respects.
def set_device(dev, cspin=None):
    global _write
    global _dummy
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
            dev.write(b'\0')  # SM is now waiting for CS low.
        _dummy = clear_sm
    else:
        print('set_device: invalid args.')

_available = set(range(0, 22))  # Valid idents are 0..21

def _validate(ident, num=1):
    if ident >= 0 and ident + num < 22:
        try:
            for x in range(ident, ident + num):
                _available.remove(x)
        except KeyError:
            raise ValueError(f'Monitor error - ident {x:02} already allocated.')
    else:
        raise ValueError(f'Monitor error - ident {ident:02} out of range.')


def monitor(n, max_instances=1):
    def decorator(coro):
        # This code runs before asyncio.run()
        _validate(n, max_instances)
        instance = 0
        async def wrapped_coro(*args, **kwargs):
            # realtime
            nonlocal instance
            d = 0x40 + n + min(instance, max_instances - 1)
            v = bytes(chr(d), 'utf8')
            instance += 1
            if instance > max_instances:
                print(f'Monitor {n:02} max_instances reached')
            _write(v)
            try:
                res = await coro(*args, **kwargs)
            except asyncio.CancelledError:
                raise
            finally:
                d |= 0x20
                v = bytes(chr(d), 'utf8')
                _write(v)
                instance -= 1
            return res
        return wrapped_coro
    return decorator

# If SPI, clears the state machine in case prior test resulted in the DUT
# crashing. It does this by sending a byte with CS\ False (high).
def monitor_init():
    _dummy()  # Does nothing if UART
    _write(b'z')

# Optionally run this to show up periods of blocking behaviour
@monitor(0)
async def _do_nowt():
    await asyncio.sleep_ms(0)

async def hog_detect():
    while True:
        await _do_nowt()

# Monitor a synchronous function definition
def mon_func(n):
    def decorator(func):
        _validate(n)
        dstart = 0x40 + n
        vstart = bytes(chr(dstart), 'utf8')
        dend = 0x60 + n
        vend = bytes(chr(dend), 'utf8')
        def wrapped_func(*args, **kwargs):
            _write(vstart)
            res = func(*args, **kwargs)
            _write(vend)
            return res
        return wrapped_func
    return decorator

        
# Monitor a synchronous function call
class mon_call:
    def __init__(self, n):
        _validate(n)
        self.n = n
        self.dstart = 0x40 + n
        self.vstart = bytes(chr(self.dstart), 'utf8')
        self.dend = 0x60 + n
        self.vend = bytes(chr(self.dend), 'utf8')

    def __enter__(self):
        _write(self.vstart)
        return self

    def __exit__(self, type, value, traceback):
        _write(self.vend)
        return False  # Don't silence exceptions
