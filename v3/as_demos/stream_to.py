# stream_to.py Demo of StreamReader with timeout.
# Hardware: Pico or Pico W with pin GPIO0 linked to GPIO1
# Copyright Peter Hinch 2024 Released under the MIT license

import asyncio
from primitives import Delay_ms
from machine import UART

_uart = UART(0, 115200, tx=0, rx=1, timeout=0)  # Adapt for other hardware

# Class extends StreamReader to enable read with timeout
class StreamReaderTo(asyncio.StreamReader):
    def __init__(self, source):
        super().__init__(source)
        self._delay_ms = Delay_ms()  # Allocate once only

    # Task cancels itself if timeout elapses without a byte being received
    async def readintotim(self, buf: bytearray, toms: int) -> int:  # toms: timeout in ms
        mvb = memoryview(buf)
        timer = self._delay_ms
        timer.callback(asyncio.current_task().cancel)
        timer.trigger(toms)  # Start cancellation timer
        n = 0
        nbytes = len(buf)
        try:
            while n < nbytes:
                n += await super().readinto(mvb[n:])
                timer.trigger(toms)  # Retrigger when bytes received
        except asyncio.CancelledError:
            pass
        timer.stop()
        return n


# Simple demo
EOT = b"QUIT"  # End of transmission


async def sender(writer):
    s = "The quick brown fox jumps over the lazy dog!"
    for _ in range(2):
        writer.write(s)
        writer.drain()
        await asyncio.sleep(1)  # < reader timeout
        writer.write(s)
        writer.drain()
        await asyncio.sleep(4)  # > reader timeout
    writer.write(EOT)
    writer.drain()


async def receiver(reader):
    buf = bytearray(16)  # Read in blocks of 16 cbytes
    print("Receiving. Demo runs for ~15s...")
    while not buf.startswith(EOT):
        n = await reader.readintotim(buf, 3000)
        if n < len(buf):
            print("Timeout: ", end="")
        print(bytes(buf[:n]))
        if n < len(buf):
            print("")
    print("Demo complete.")


async def main():
    reader = StreamReaderTo(_uart)
    writer = asyncio.StreamWriter(_uart, {})
    await asyncio.gather(sender(writer), receiver(reader))


try:
    asyncio.run(main())
finally:
    _ = asyncio.new_event_loop()
