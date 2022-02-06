# iorw.py Emulate a device which can read and write one character at a time.

# Slow hardware is emulated using timers.
# MyIO.write() ouputs a single character and sets the hardware not ready.
# MyIO.readline() returns a single character and sets the hardware not ready.
# Timers asynchronously set the hardware ready.

import io, pyb
import uasyncio as asyncio
import micropython
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
        self.ready_rd = False  # Set by timer cb do_input
        ch = self.rbuf[self.ridx]
        if ch == ord('\n'):
            self.ridx = 0
        else:
            self.ridx += 1
        return chr(ch)

    # Emulate unbuffered hardware which writes one character: uasyncio waits
    # until hardware is ready for the next. Hardware ready is emulated by write
    # timer callback.
    def write(self, buf, off=0, sz=0):
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

def printexp():
    st = '''Received b'ready\\n'
Received b'ready\\n'
Received b'ready\\n'
Received b'ready\\n'
Received b'ready\\n'
Wrote Hello MyIO 1
Received b'ready\\n'
Received b'ready\\n'
Received b'ready\\n'
Wrote Hello MyIO 2
Received b'ready\\n'
...
Runs until interrupted (ctrl-c).
'''
    print('\x1b[32m')
    print(st)
    print('\x1b[39m')

printexp()
myio = MyIO()
asyncio.create_task(receiver(myio))
asyncio.run(sender(myio))
