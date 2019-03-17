# uclient.py Demo of simple uasyncio-based client for echo server

# Released under the MIT licence
# Copyright (c) Peter Hinch 2019

import usocket as socket
import uasyncio as asyncio
import ujson
from heartbeat import heartbeat  # Optional LED flash

server = '192.168.0.32'
port = 8123

async def run():
    sock = socket.socket()
    def close():
        sock.close()
        print('Server disconnect.')
    try:
        serv = socket.getaddrinfo(server, port)[0][-1]
        sock.connect(serv)
    except OSError as e:
        print('Cannot connect to {} on port {}'.format(server, port))
        sock.close()
        return
    while True:
        sreader = asyncio.StreamReader(sock)
        swriter = asyncio.StreamWriter(sock, {})
        data = ['value', 1]
        while True:
            try:
                await swriter.awrite('{}\n'.format(ujson.dumps(data)))
                res = await sreader.readline()
            except OSError:
                close()
                return
            try:
                print('Received', ujson.loads(res))
            except ValueError:
                close()
                return
            await asyncio.sleep(2)
            data[1] += 1

loop = asyncio.get_event_loop()
# Optional fast heartbeat to confirm nonblocking operation
loop.create_task(heartbeat(100))
try:
    loop.run_until_complete(run())
except KeyboardInterrupt:
    print('Interrupted')  # This mechanism doesn't work on Unix build.
