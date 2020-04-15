# baud.py Test uasyncio at high baudrate
import pyb
import uasyncio as asyncio
import utime
import as_drivers.as_rwGPS as as_rwGPS
# Outcome
# Sleep Buffer
# 0     None    OK, length limit 74
# 10    None    Bad: length 111 also short weird RMC sentences
# 10    1000    OK, length 74, 37
# 10    200     Bad: 100, 37 overruns
# 10    400     OK, 74,24 Short GSV sentence looked OK
# 4     200     OK, 74,35 Emulate parse time

# as_GPS.py
# As written update blocks for 23.5ms parse for 3.8ms max
# with CRC check removed update blocks 17.3ms max
# CRC, bad char and line length removed update blocks 8.1ms max

# At 10Hz update rate I doubt there's enough time to process the data
BAUDRATE = 115200
red, green, yellow, blue = pyb.LED(1), pyb.LED(2), pyb.LED(3), pyb.LED(4)

async def setup():
    print('Initialising')
    uart = pyb.UART(4, 9600)
    sreader = asyncio.StreamReader(uart)
    swriter = asyncio.StreamWriter(uart, {})
    gps = as_rwGPS.GPS(sreader, swriter, local_offset=1)
    await asyncio.sleep(2)
    await gps.baudrate(BAUDRATE)
    uart.init(BAUDRATE)

def setbaud():
    asyncio.run(setup())
    print('Baudrate set to 115200.')

async def gps_test():
    print('Initialising')
    uart = pyb.UART(4, BAUDRATE, read_buf_len=400)
    sreader = asyncio.StreamReader(uart)
    swriter = asyncio.StreamWriter(uart, {})
    maxlen = 0
    minlen = 100
    while True:
        res = await sreader.readline()
        l = len(res)
        maxlen = max(maxlen, l)
        minlen = min(minlen, l)
        print(l, maxlen, minlen, res)
        red.toggle()
        utime.sleep_ms(10)

def test():
    asyncio.run(gps_test())
