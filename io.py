import uasyncio as asyncio

MP_STREAM_POLL_RD = 1
MP_STREAM_POLL = 3

# Get address of object not supporting the buffer protocol
#@micropython.asm_thumb
#def addressof(r0):
#    nop()

class Device():
    def __init__(self):
        self.ready = False

    def fileno(self):
        return 999 # 'runs' without error in Unix, on Pyboard mp_get_stream_raise() sees stream_p == NULL
    # Runs in the sense that the read loop keeps iterating
#        print(hex(addressof(self)))
#        return addressof(self)

    def ioctl(self, cmd, flags):
        res = 0
        print('Got here')
        if cmd == MP_STREAM_POLL and (flags & MP_STREAM_POLL_RD):
            if self.ready:
                res = MP_STREAM_POLL_RD
        return res

    def read(self):
        return
    def write(self):
        return

    async def readloop(self):
        while True:
            print('About to yield')
            yield asyncio.IORead(self)
            print('Should never happen')

loop = asyncio.get_event_loop()
device = Device()
loop.create_task(device.readloop())
loop.run_forever()
