# log_kml.py Log GPS data to a kml file for display on Google Earth

# Copyright (c) Peter Hinch 2018-2020
# MIT License (MIT) - see LICENSE file
# Test program for asynchronous GPS device driver as_pyGPS
# KML file format: https://developers.google.com/kml/documentation/kml_tut
# http://www.toptechboy.com/arduino/lesson-25-display-your-gps-data-as-track-on-google-earth/

# Remove blue LED for Pyboard D

# Logging stops and the file is closed when the user switch is pressed.

import as_GPS
import uasyncio as asyncio
import pyb

str_start = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<Style id="yellowPoly">
<LineStyle>
<color>7f00ffff</color>
<width>4</width>
</LineStyle>
<PolyStyle>
<color>7f00ff00</color>
</PolyStyle>
</Style>
<Placemark><styleUrl>#yellowPoly</styleUrl>
<LineString>
<extrude>1</extrude>
<tesselate>1</tesselate>
<altitudeMode>absolute</altitudeMode>
<coordinates>
'''

str_end = '''
</coordinates>
</LineString></Placemark>
 
</Document></kml>
'''

red, green, yellow = pyb.LED(1), pyb.LED(2), pyb.LED(3)
sw = pyb.Switch()

# Toggle the red LED
def toggle_led(*_):
    red.toggle()

async def log_kml(fn='/sd/log.kml', interval=10):
    yellow.on()  # Waiting for data
    uart = pyb.UART(4, 9600, read_buf_len=200)  # Data on X2
    sreader = asyncio.StreamReader(uart)
    gps = as_GPS.AS_GPS(sreader, fix_cb=toggle_led)
    await gps.data_received(True, True, True, True)
    yellow.off()
    with open(fn, 'w') as f:
        f.write(str_start)
        while not sw.value():
            f.write(gps.longitude_string(as_GPS.KML))
            f.write(',')
            f.write(gps.latitude_string(as_GPS.KML))
            f.write(',')
            f.write(str(gps.altitude))
            f.write('\r\n')
            for _ in range(interval * 10):
                await asyncio.sleep_ms(100)
                if sw.value():
                    break

        f.write(str_end)
    red.off()
    green.on()

loop = asyncio.get_event_loop()
loop.run_until_complete(log_kml())
