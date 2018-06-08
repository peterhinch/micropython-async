# iotest4.py Test PR #3836. Demonstrate the anomaly with a read/write device.
# User class write() performs unbuffered writing.
# For simplicity this uses buffered read: unbuffered is tested by iotest2.py.

# Run iotest4.test() to see expected output
# iotest4.test(False) to demonstrate the issue.

# Pass/Fail is determined by whether the StreamReader and StreamWriter operate
# on the same (fail) or different (pass) objects.
# I suspect that the issue is with select/ipoll (uasyncio __init__.py)
# The fault is either in select/poll or uasyncio __init__.py.
# As soon as PollEventLoop.add_writer() is called, reading stops.
# PollEventLoop.add_writer() is called when StreamWriter.awrite() issues
# yield IOWrite(self.s), which for unbuffered devices is after the 1st char
# of a multi-char buf is written.

import io, pyb
import uasyncio as asyncio
import micropython
micropython.alloc_emergency_exception_buf(100)

MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL_WR = const(4)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

def printbuf(this_io):
    print(this_io.wbuf[:this_io.wprint_len])

class MyIO(io.IOBase):
    def __init__(self, read=False, write=False):
        if read:
            self.ready_rd = False
            self.rbuf = b'ready\n'  # Read buffer
            pyb.Timer(4, freq = 1, callback = self.do_input)
        if write:
            self.wbuf = bytearray(100)  # Write buffer
            self.wprint_len = 0
            self.widx = 0
            self.wch = b''
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

    # Emulate a device with buffered read. Return the buffer, falsify read ready
    # Read timer sets ready.
    def readline(self):
        self.ready_rd = False
        return self.rbuf

    # Emulate unbuffered hardware which writes one character: uasyncio waits
    # until hardware is ready for the next. Hardware ready is emulated by write
    # timer callback.
    def write(self, buf, off, sz):
        self.wch = buf[off]  # Hardware starts to write a char
        return 1  # 1 byte written. uasyncio waits on ioctl write ready

async def receiver(myior):
    sreader = asyncio.StreamReader(myior)
    while True:
        res = await sreader.readline()
        print('Received', res)

async def sender(myiow):
    swriter = asyncio.StreamWriter(myiow, {})
    await asyncio.sleep(5)
    count = 0
    while True:
        count += 1
        tosend = 'Wrote Hello MyIO {}\n'.format(count)
        await swriter.awrite(tosend.encode('UTF8'))
        await asyncio.sleep(2)

def test(good=True):
    if good:
        myior = MyIO(read=True)
        myiow = MyIO(write=True)
    else:
        myior = MyIO(read=True, write=True)
        myiow = myior
    loop = asyncio.get_event_loop()
    loop.create_task(receiver(myior))
    loop.create_task(sender(myiow))
    loop.run_forever()
