# iorw_to.py Emulate a device which can read and write one character at a time
# and test timeouts.

# Copyright (c) Peter Hinch 2019
# Released under the MIT licence

# This requires the modified version of uasyncio (fast_io directory).
# Slow hardware is emulated using timers.
# MyIO.write() ouputs a single character and sets the hardware not ready.
# MyIO.readline() returns a single character and sets the hardware not ready.
# Timers asynchronously set the hardware ready.

import io, pyb
import uasyncio as asyncio
import micropython
import sys
try:
    print('Uasyncio version', asyncio.version)
    if not isinstance(asyncio.version, tuple):
        print('Please use fast_io version 0.24 or later.')
        sys.exit(0)
except AttributeError:
    print('ERROR: This test requires the fast_io version. It will not run correctly')
    print('under official uasyncio V2.0 owing to a bug which prevents concurrent')
    print('input and output.')
    sys.exit(0)

print('Issue iorw_to.test(True) to test ioq, iorw_to.test() to test runq.')
print('Test runs until interrupted. Tasks time out after 15s.')
print('Issue ctrl-d after each run.')

micropython.alloc_emergency_exception_buf(100)

MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL_WR = const(4)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

def printbuf(this_io):
    print(bytes(this_io.wbuf[:this_io.wprint_len]).decode(), end='')

class MyIO(io.IOBase):
    def __init__(self, read=False, write=False):
        self.ready_rd = False  # Read and write not ready
        self.rbuf = b'ready\n'  # Read buffer
        self.ridx = 0
        pyb.Timer(4, freq = 5, callback = self.do_input)
        self.wch = b''
        self.wbuf = bytearray(100)  # Write buffer
        self.wprint_len = 0
        self.widx = 0
        pyb.Timer(5, freq = 10, callback = self.do_output)

    # Read callback: emulate asynchronous input from hardware.
    # Typically would put bytes into a ring buffer and set .ready_rd.
    def do_input(self, t):
        self.ready_rd = True  # Data is ready to read

    # Write timer callback. Emulate hardware: if there's data in the buffer
    # write some or all of it
    def do_output(self, t):
        if self.wch:
            self.wbuf[self.widx] = self.wch
            self.widx += 1
            if self.wch == ord('\n'):
                self.wprint_len = self.widx  # Save for schedule
                micropython.schedule(printbuf, self)
                self.widx = 0
        self.wch = b''


    def ioctl(self, req, arg):  # see ports/stm32/uart.c
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                if self.ready_rd:
                    ret |= MP_STREAM_POLL_RD
            if arg & MP_STREAM_POLL_WR:
                if not self.wch:
                    ret |= MP_STREAM_POLL_WR  # Ready if no char pending
        return ret

    # Test of device that produces one character at a time
    def readline(self):
        self.ready_rd = False  # Cleared by timer cb do_input
        ch = self.rbuf[self.ridx]
        if ch == ord('\n'):
            self.ridx = 0
        else:
            self.ridx += 1
        return chr(ch)

    # Emulate unbuffered hardware which writes one character: uasyncio waits
    # until hardware is ready for the next. Hardware ready is emulated by write
    # timer callback.
    def write(self, buf, off, sz):
        self.wch = buf[off]  # Hardware starts to write a char
        return 1  # 1 byte written. uasyncio waits on ioctl write ready

# Note that trapping the exception and returning is still mandatory.
async def receiver(myior):
    sreader = asyncio.StreamReader(myior)
    try:
        while True:
            res = await sreader.readline()
            print('Received', res)
    except asyncio.TimeoutError:
        print('Receiver timeout')

async def sender(myiow):
    swriter = asyncio.StreamWriter(myiow, {})
    await asyncio.sleep(1)
    count = 0
    try:  # Trap in outermost scope to catch cancellation of .sleep
        while True:
            count += 1
            tosend = 'Wrote Hello MyIO {}\n'.format(count)
            await swriter.awrite(tosend.encode('UTF8'))
            await asyncio.sleep(2)
    except asyncio.TimeoutError:
        print('Sender timeout')

async def run(coro, t):
    await asyncio.wait_for_ms(coro, t)

async def do_test(loop, t):
    myio = MyIO()
    while True:
        tr = t * 1000 + (pyb.rng() >> 20)  # Add ~1s uncertainty
        tw = t * 1000 + (pyb.rng() >> 20)
        print('Timeouts: {:7.3f}s read {:7.3f}s write'.format(tr/1000, tw/1000))
        loop.create_task(run(receiver(myio), tr))
        await run(sender(myio), tw)
        await asyncio.sleep(2)  # Wait out timing randomness

def test(ioq=False):
    if ioq:
        loop = asyncio.get_event_loop(ioq_len=16)
    else:
        loop = asyncio.get_event_loop()
    loop.create_task(do_test(loop, 15))
    loop.run_forever()
