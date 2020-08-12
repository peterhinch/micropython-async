# userver.py Demo of simple uasyncio-based echo server

# Released under the MIT licence
# Copyright (c) Peter Hinch 2019

import usocket as socket
import uasyncio as asyncio
import uselect as select
import ujson
from heartbeat import heartbeat  # Optional LED flash

class Server:

    async def run(self, port=8123):
        print('Awaiting client connection.')
        self.cid = 0
        asyncio.create_task(heartbeat(100))
        self.server = await asyncio.start_server(self.run_client, '0.0.0.0', port)
        while True:
            await asyncio.sleep(100)

    async def run_client(self, sreader, swriter):
        self.cid += 1
        print('Got connection from client', self.cid)
        try:
            while True:
                res = await sreader.readline()
                if res == b'':
                    raise OSError
                print('Received {} from client {}'.format(ujson.loads(res.rstrip()), self.cid))
                swriter.write(res)
                await swriter.drain()  # Echo back
        except OSError:
            pass
        print('Client {} disconnect.'.format(self.cid))
        await sreader.wait_closed()
        print('Client {} socket closed.'.format(self.cid))

    def close(self):
        print('Closing server')
        self.server.close()
        await self.server.wait_closed()
        print('Server closed')

server = Server()
try:
    asyncio.run(server.run())
except KeyboardInterrupt:
    print('Interrupted')  # This mechanism doesn't work on Unix build.
finally:
    server.close()
    _ = asyncio.new_event_loop()
