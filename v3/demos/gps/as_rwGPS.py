# as_rwGPS.py Asynchronous device driver for GPS devices using a UART.
# Supports a limited subset of the PMTK command packets employed by the
# widely used MTK3329/MTK3339 chip.
# Sentence parsing based on MicropyGPS by Michael Calvin McCoy
# https://github.com/inmcm/micropyGPS

# Copyright (c) 2018 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import as_GPS
try:
    from micropython import const
except ImportError:
    const = lambda x : x

HOT_START = const(1)
WARM_START = const(2)
COLD_START = const(3)
FULL_COLD_START = const(4)
STANDBY = const(5)
DEFAULT_SENTENCES = const(6)
VERSION = const(7)
ENABLE = const(8)
ANTENNA = const(9)
NO_ANTENNA = const(10)

# Return CRC of a bytearray.
def _crc(sentence):
    x = 1
    crc = 0
    while sentence[x] != ord('*'):
        crc ^= sentence[x]
        x += 1
    return crc  # integer


class GPS(as_GPS.AS_GPS):
    fixed_commands = {HOT_START: b'$PMTK101*32\r\n',
                      WARM_START: b'$PMTK102*31\r\n',
                      COLD_START: b'$PMTK103*30\r\n',
                      FULL_COLD_START: b'$PMTK104*37\r\n',
                      STANDBY: b'$PMTK161,0*28\r\n',
                      DEFAULT_SENTENCES: b'$PMTK314,-1*04\r\n',
                      VERSION: b'$PMTK605*31\r\n',
                      ENABLE: b'$PMTK414*33\r\n',
                      ANTENNA: b'$PGCMD,33,1*6C',
                      NO_ANTENNA: b'$PGCMD,33,0*6D',
                      }

    def __init__(self, sreader, swriter, local_offset=0,
                 fix_cb=lambda *_ : None, cb_mask=as_GPS.RMC, fix_cb_args=(),
                 msg_cb=lambda *_ : None, msg_cb_args=()):
        super().__init__(sreader, local_offset, fix_cb, cb_mask, fix_cb_args)
        self._swriter = swriter
        self.version = None  # Response to VERSION query
        self.enabled = None  # Response to ENABLE query
        self.antenna = 0  # Response to ANTENNA.
        self._msg_cb = msg_cb
        self._msg_cb_args = msg_cb_args

    async def _send(self, sentence):
        # Create a bytes object containing hex CRC
        bcrc = '{:2x}'.format(_crc(sentence)).encode()
        sentence[-4] = bcrc[0]  # Fix up CRC bytes
        sentence[-3] = bcrc[1]
        await self._swriter.awrite(sentence)

    async def baudrate(self, value=9600):
        if value not in (4800,9600,14400,19200,38400,57600,115200):
            raise ValueError('Invalid baudrate {:d}.'.format(value))

        sentence = bytearray('$PMTK251,{:d}*00\r\n'.format(value))
        await self._send(sentence)

    async def update_interval(self, ms=1000):
        if ms < 100 or ms > 10000:
            raise ValueError('Invalid update interval {:d}ms.'.format(ms))
        sentence = bytearray('$PMTK220,{:d}*00\r\n'.format(ms))
        await self._send(sentence)
        self._update_ms = ms  # Save for timing driver

    async def enable(self, *, gll=0, rmc=1, vtg=1, gga=1, gsa=1, gsv=5, chan=0):
        fstr = '$PMTK314,{:d},{:d},{:d},{:d},{:d},{:d},0,0,0,0,0,0,0,0,0,0,0,0,{:d}*00\r\n'
        sentence = bytearray(fstr.format(gll, rmc, vtg, gga, gsa, gsv, chan))
        await self._send(sentence)

    async def command(self, cmd):
        if cmd not in self.fixed_commands:
            raise ValueError('Invalid command {:s}.'.format(cmd))
        await self._swriter.awrite(self.fixed_commands[cmd])

    # Should get 705 from VERSION 514 from ENABLE
    def parse(self, segs):
        if segs[0] == 'PMTK705':  # Version response
            self.version = segs[1:]
            segs[0] = 'version'
            self._msg_cb(self, segs, *self._msg_cb_args)
            return True

        if segs[0] == 'PMTK514':
            print('enabled segs', segs)
            self.enabled = {'gll': segs[1], 'rmc': segs[2], 'vtg': segs[3],
                            'gga': segs[4], 'gsa': segs[5], 'gsv': segs[6],
                            'chan': segs[19]}
            segs = ['enabled', self.enabled]
            self._msg_cb(self, segs, *self._msg_cb_args)
            return True
 
        if segs[0] == 'PGTOP':
            self.antenna = segs[2]
            segs = ['antenna', self.antenna]
            self._msg_cb(self, segs, *self._msg_cb_args)
            return True

        if segs[0][:4] == 'PMTK':
            self._msg_cb(self, segs, *self._msg_cb_args)
            return True
        return False
