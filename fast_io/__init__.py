# uasyncio.__init__ fast_io
# (c) 2014-2018 Paul Sokolovsky. MIT license.

# This is a fork of official MicroPython uasynco. It is recommended to use
# the official version unless the specific features of this fork are required.

# Changes copyright (c) Peter Hinch 2018
# Code at https://github.com/peterhinch/micropython-async.git
# fork: peterhinch/micropython-lib branch: uasyncio-io-fast-and-rw

import uerrno
import uselect as select
import usocket as _socket
from uasyncio.core import *

DEBUG = 0
log = None

def set_debug(val):
    global DEBUG, log
    DEBUG = val
    if val:
        import logging
        log = logging.getLogger("uasyncio")

# add_writer causes read failure if passed the same sock instance as was passed
# to add_reader. Cand we fix this by maintaining two object maps?
class PollEventLoop(EventLoop):

    def __init__(self, runq_len=16, waitq_len=16, fast_io=0, lp_len=0):
        EventLoop.__init__(self, runq_len, waitq_len, fast_io, lp_len)
        self.poller = select.poll()
        self.rdobjmap = {}
        self.wrobjmap = {}
        self.flags = {}

    # Remove registration of sock for reading or writing.
    def _unregister(self, sock, objmap, flag):
        # If StreamWriter.awrite() wrote entire buf on 1st pass sock will never
        # have been registered. So test for presence in .flags.
        if id(sock) in self.flags:
            flags = self.flags[id(sock)]
            if flags & flag:  # flag is currently registered
                flags &= ~flag  # Clear current flag
                if flags:  # Another flag is present
                    self.flags[id(sock)] = flags
                    self.poller.register(sock, flags)
                else:
                    del self.flags[id(sock)]  # Clear all flags
                    self.poller.unregister(sock)
                del objmap[id(sock)]  # Remove coro from appropriate dict

    # Additively register sock for reading or writing
    def _register(self, sock, flag):
        if id(sock) in self.flags:
            self.flags[id(sock)] |= flag
        else:
            self.flags[id(sock)] = flag
        self.poller.register(sock, self.flags[id(sock)])

    def add_reader(self, sock, cb, *args):
        if DEBUG and __debug__:
            log.debug("add_reader%s", (sock, cb, args))
        self._register(sock, select.POLLIN)
        if args:
            self.rdobjmap[id(sock)] = (cb, args)
        else:
            self.rdobjmap[id(sock)] = cb

    def remove_reader(self, sock):
        if DEBUG and __debug__:
            log.debug("remove_reader(%s)", sock)
        self._unregister(sock, self.rdobjmap, select.POLLIN)

    def add_writer(self, sock, cb, *args):
        if DEBUG and __debug__:
            log.debug("add_writer%s", (sock, cb, args))
        self._register(sock, select.POLLOUT)
        if args:
            self.wrobjmap[id(sock)] = (cb, args)
        else:
            self.wrobjmap[id(sock)] = cb

    def remove_writer(self, sock):
        if DEBUG and __debug__:
            log.debug("remove_writer(%s)", sock)
        self._unregister(sock, self.wrobjmap, select.POLLOUT)

    def wait(self, delay):
        if DEBUG and __debug__:
            log.debug("poll.wait(%d)", delay)
        # We need one-shot behavior (second arg of 1 to .poll())
        res = self.poller.ipoll(delay, 1)
        #log.debug("poll result: %s", res)
        for sock, ev in res:
            if ev & select.POLLOUT:
                cb = self.wrobjmap[id(sock)]
                if cb is None:
                    continue  # Not yet ready.
                # Invalidate objmap: can get adverse timing in fast_io whereby add_writer
                # is not called soon enough. Ignore poll events occurring before we are
                # ready to handle them.
                self.wrobjmap[id(sock)] = None
                if ev & (select.POLLHUP | select.POLLERR):
                    # These events are returned even if not requested, and
                    # are sticky, i.e. will be returned again and again.
                    # If the caller doesn't do proper error handling and
                    # unregister this sock, we'll busy-loop on it, so we
                    # as well can unregister it now "just in case".
                    self.remove_writer(sock)
                if DEBUG and __debug__:
                    log.debug("Calling IO callback: %r", cb)
                if isinstance(cb, tuple):
                    cb[0](*cb[1])
                else:
                    prev = cb.pend_throw(None)  # Enable task to run.
                    #if isinstance(prev, Exception):
                        #print('Put back exception')
                        #cb.pend_throw(prev)
                    self._call_io(cb)  # Put coro onto runq (or ioq if one exists)
            if ev & select.POLLIN:
                cb = self.rdobjmap[id(sock)]
                if cb is None:
                    continue
                self.rdobjmap[id(sock)] = None
                if ev & (select.POLLHUP | select.POLLERR):
                    # These events are returned even if not requested, and
                    # are sticky, i.e. will be returned again and again.
                    # If the caller doesn't do proper error handling and
                    # unregister this sock, we'll busy-loop on it, so we
                    # as well can unregister it now "just in case".
                    self.remove_reader(sock)
                if DEBUG and __debug__:
                    log.debug("Calling IO callback: %r", cb)
                if isinstance(cb, tuple):
                    cb[0](*cb[1])
                else:
                    prev = cb.pend_throw(None)  # Enable task to run.
                    #if isinstance(prev, Exception):
                        #cb.pend_throw(prev)
                        #print('Put back exception')
                    self._call_io(cb)


class StreamReader:

    def __init__(self, polls, ios=None):
        if ios is None:
            ios = polls
        self.polls = polls
        self.ios = ios

    def read(self, n=-1):
        while True:
            yield IORead(self.polls)
            res = self.ios.read(n)  # Call the device's read method
            if res is not None:
                break
            # This should not happen for real sockets, but can easily
            # happen for stream wrappers (ssl, websockets, etc.)
            #log.warn("Empty read")
        yield IOReadDone(self.polls)  # uasyncio.core calls remove_reader
        # This de-registers device as a read device with poll via
        # PollEventLoop._unregister
        return res  # Next iteration raises StopIteration and returns result

    def readexactly(self, n):
        buf = b""
        while n:
            yield IORead(self.polls)
            res = self.ios.read(n)
            assert res is not None
            if not res:
                break
            buf += res
            n -= len(res)
        yield IOReadDone(self.polls)
        return buf

    def readline(self):
        if DEBUG and __debug__:
            log.debug("StreamReader.readline()")
        buf = b""
        while True:
            yield IORead(self.polls)
            res = self.ios.readline()
            assert res is not None
            if not res:
                break
            buf += res
            if buf[-1] == 0x0a:
                break
        if DEBUG and __debug__:
            log.debug("StreamReader.readline(): %s", buf)
        yield IOReadDone(self.polls)
        return buf

    def aclose(self):
        yield IOReadDone(self.polls)
        self.ios.close()

    def __repr__(self):
        return "<StreamReader %r %r>" % (self.polls, self.ios)


class StreamWriter:

    def __init__(self, s, extra):
        self.s = s
        self.extra = extra

    def awrite(self, buf, off=0, sz=-1):
        # This method is called awrite (async write) to not proliferate
        # incompatibility with original asyncio. Unlike original asyncio
        # whose .write() method is both not a coroutine and guaranteed
        # to return immediately (which means it has to buffer all the
        # data), this method is a coroutine.
        if sz == -1:
            sz = len(buf) - off
        if DEBUG and __debug__:
            log.debug("StreamWriter.awrite(): spooling %d bytes", sz)
        while True:
            res = self.s.write(buf, off, sz)
            # If we spooled everything, return immediately
            if res == sz:
                if DEBUG and __debug__:
                    log.debug("StreamWriter.awrite(): completed spooling %d bytes", res)
                yield IOWriteDone(self.s)  # remove_writer de-registers device as a writer
                return
            if res is None:
                res = 0
            if DEBUG and __debug__:
                log.debug("StreamWriter.awrite(): spooled partial %d bytes", res)
            assert res < sz
            off += res
            sz -= res
            yield IOWrite(self.s)
            #assert s2.fileno() == self.s.fileno()
            if DEBUG and __debug__:
                log.debug("StreamWriter.awrite(): can write more")

    # Write piecewise content from iterable (usually, a generator)
    def awriteiter(self, iterable):
        for buf in iterable:
            yield from self.awrite(buf)

    def aclose(self):
        yield IOWriteDone(self.s)
        self.s.close()

    def get_extra_info(self, name, default=None):
        return self.extra.get(name, default)

    def __repr__(self):
        return "<StreamWriter %r>" % self.s


def open_connection(host, port, ssl=False):
    if DEBUG and __debug__:
        log.debug("open_connection(%s, %s)", host, port)
    ai = _socket.getaddrinfo(host, port, 0, _socket.SOCK_STREAM)
    ai = ai[0]
    s = _socket.socket(ai[0], ai[1], ai[2])
    s.setblocking(False)
    try:
        s.connect(ai[-1])
    except OSError as e:
        if e.args[0] != uerrno.EINPROGRESS:
            raise
    if DEBUG and __debug__:
        log.debug("open_connection: After connect")
    yield IOWrite(s)
#    if __debug__:
#        assert s2.fileno() == s.fileno()
    if DEBUG and __debug__:
        log.debug("open_connection: After iowait: %s", s)
    if ssl:
        print("Warning: uasyncio SSL support is alpha")
        import ussl
        s.setblocking(True)
        s2 = ussl.wrap_socket(s)
        s.setblocking(False)
        return StreamReader(s, s2), StreamWriter(s2, {})
    return StreamReader(s), StreamWriter(s, {})


def start_server(client_coro, host, port, backlog=10):
    if DEBUG and __debug__:
        log.debug("start_server(%s, %s)", host, port)
    ai = _socket.getaddrinfo(host, port, 0, _socket.SOCK_STREAM)
    ai = ai[0]
    s = _socket.socket(ai[0], ai[1], ai[2])
    s.setblocking(False)

    s.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
    s.bind(ai[-1])
    s.listen(backlog)
    while True:
        if DEBUG and __debug__:
            log.debug("start_server: Before accept")
        yield IORead(s)
        if DEBUG and __debug__:
            log.debug("start_server: After iowait")
        s2, client_addr = s.accept()
        s2.setblocking(False)
        if DEBUG and __debug__:
            log.debug("start_server: After accept: %s", s2)
        extra = {"peername": client_addr}
        yield client_coro(StreamReader(s2), StreamWriter(s2, extra))


import uasyncio.core
uasyncio.core._event_loop_class = PollEventLoop
