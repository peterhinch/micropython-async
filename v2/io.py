# io.py Failed attempt to use uasyncio IORead mechanism in a custom class.
# It turns out that the necessary support has not been implemented, and
# it is unlikely that this will occur.
import uasyncio as asyncio

MP_STREAM_POLL_RD = 1
MP_STREAM_POLL = 3

import uasyncio as asyncio
class Device():
    def __init__(self):
        self.ready = False

    def fileno(self):
        return 999

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
