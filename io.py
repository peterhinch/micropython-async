try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

MP_STREAM_POLL_RD = 1
MP_STREAM_POLL = 3

# Get address of object not supporting the buffer protocol
@micropython.asm_thumb
def addressof(r0):
    nop()


class Device(object):
    def __init__(self):
        self.ready = False

    def fileno(self):
        print(hex(addressof(self)))
        return addressof(self)

    def ioctl(self, cmd, flags):
        res = 0
        print('Got here')
        if cmd == MP_STREAM_POLL and (flags & MP_STREAM_POLL_RD):
            if self.ready:
                res = MP_STREAM_POLL_RD
        return res

    async def readloop(self):
        while True:
            print('About to yield')
            yield asyncio.IORead(self)
            print('Should never happen')

loop = asyncio.get_event_loop()
device = Device()
loop.call_soon(device.readloop())
loop.run_forever()
