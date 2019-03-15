# userver.py Demo of simple uasyncio-based echo server

# Released under the MIT licence
# Copyright (c) Peter Hinch 2019

import usocket as socket
import uasyncio as asyncio
import uselect as select
import ujson

class Server:
    @staticmethod
    async def flash():  # ESP8266 only: demo that it is nonblocking
        from machine import Pin
        pin = Pin(2, Pin.OUT)
        while True:
            pin(not pin())
            await asyncio.sleep_ms(100)

    async def run(self, loop, port=8123, led=True):
        addr = socket.getaddrinfo('0.0.0.0', port, 0, socket.SOCK_STREAM)[0][-1]
        s_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # server socket
        s_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_sock.bind(addr)
        s_sock.listen(5)
        self.socks = [s_sock]  # List of current sockets for .close()
        print('Awaiting connection on port', port)
        poller = select.poll()
        poller.register(s_sock, select.POLLIN)
        client_id = 1  # For user feedback
        if led:
            loop.create_task(self.flash())
        while True:
            res = poller.poll(1)  # 1ms block
            if res:  # Only s_sock is polled
                c_sock, _ = s_sock.accept()  # get client socket
                loop.create_task(self.run_client(c_sock, client_id))
                client_id += 1
            await asyncio.sleep_ms(200)

    async def run_client(self, sock, cid):
        self.socks.append(sock)
        sreader = asyncio.StreamReader(sock)
        swriter = asyncio.StreamWriter(sock, {})
        print('Got connection from client', cid)
        try:
            while True:
                res = await sreader.readline()
                if res == b'':
                    raise OSError
                print('Received {} from client {}'.format(ujson.loads(res.rstrip()), cid))
                await swriter.awrite(res)  # Echo back
        except OSError:
            pass
        print('Client {} disconnect.'.format(cid))
        sock.close()
        self.socks.remove(sock)

    def close(self):
        print('Closing {} sockets.'.format(len(self.socks)))
        for sock in self.socks:
            sock.close()

loop = asyncio.get_event_loop()
server = Server()
try:
    loop.run_until_complete(server.run(loop))
except KeyboardInterrupt:
    print('Interrupted')  # This mechanism doesn't work on Unix build.
finally:
    server.close()
