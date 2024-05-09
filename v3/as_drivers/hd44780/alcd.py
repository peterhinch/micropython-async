# LCD class for Micropython and uasyncio.
# Author: Peter Hinch
# Copyright Peter Hinch 2017 Released under the MIT license
# V1.1 24 Apr 2020 Updated for uasyncio V3
# V1.0 13 May 2017

# Assumes an LCD with standard Hitachi HD44780 controller chip wired using four data lines
# Code has only been tested on two line LCD displays.

# My code is based on this program written for the Raspberry Pi
# http://www.raspberrypi-spy.co.uk/2012/07/16x2-lcd-module-control-using-python/
# HD44780 LCD Test Script for
# Raspberry Pi
#
# Author : Matt Hawkins
# Site   : http://www.raspberrypi-spy.co.uk

from machine import Pin
import utime as time
import asyncio

# ********************************** GLOBAL CONSTANTS: TARGET BOARD PIN NUMBERS *************************************

# Supply board pin numbers as a tuple in order Rs, E, D4, D5, D6, D7

PINLIST = ("Y1", "Y2", "Y6", "Y5", "Y4", "Y3")  # As used in testing.

# **************************************************** LCD CLASS ****************************************************
# Initstring:
# 0x33, 0x32: See flowchart P24 send 3,3,3,2
# 0x28: Function set DL = 1 (4 bit) N = 1 (2 lines) F = 0 (5*8 bit font)
# 0x0C: Display on/off: D = 1 display on C, B = 0 cursor off, blink off
# 0x06: Entry mode set: ID = 1 increment S = 0 display shift??
# 0x01: Clear display, set DDRAM address = 0
# Original code had timing delays of 50uS. Testing with the Pi indicates that time.sleep() can't issue delays shorter
# than about 250uS. There also seems to be an error in the original code in that the datasheet specifies a delay of
# >4.1mS after the first 3 is sent. To simplify I've imposed a delay of 5mS after each initialisation pulse: the time to
# initialise is hardly critical. The original code worked, but I'm happier with something that complies with the spec.

# Async version:
# No point in having a message queue: people's eyes aren't that quick. Just display the most recent data for each line.
# Assigning changed data to the LCD object sets a "dirty" flag for that line. The LCD's runlcd thread then updates the
# hardware and clears the flag

# lcd_byte and lcd_nybble method use explicit delays. This is because execution
# time is short relative to general latency (on the order of 300μs).


class LCD:  # LCD objects appear as read/write lists
    INITSTRING = b"\x33\x32\x28\x0C\x06\x01"
    LCD_LINES = b"\x80\xC0"  # LCD RAM address for the 1st and 2nd line (0 and 40H)
    CHR = True
    CMD = False
    E_PULSE = 50  # Timing constants in uS
    E_DELAY = 50

    def __init__(self, pinlist, cols, rows=2):  # Init with pin nos for enable, rs, D4, D5, D6, D7
        self.initialising = True
        self.LCD_E = Pin(pinlist[1], Pin.OUT)  # Create and initialise the hardware pins
        self.LCD_RS = Pin(pinlist[0], Pin.OUT)
        self.datapins = [Pin(pin_name, Pin.OUT) for pin_name in pinlist[2:]]
        self.cols = cols
        self.rows = rows
        self.lines = [""] * self.rows
        self.dirty = [False] * self.rows
        for thisbyte in LCD.INITSTRING:
            self.lcd_byte(thisbyte, LCD.CMD)
            self.initialising = False  # Long delay after first byte only
        asyncio.create_task(self.runlcd())

    def lcd_nybble(self, bits):  # send the LS 4 bits
        for pin in self.datapins:
            pin.value(bits & 0x01)
            bits >>= 1
        time.sleep_us(LCD.E_DELAY)  # 50μs
        self.LCD_E.value(True)  # Toggle the enable pin
        time.sleep_us(LCD.E_PULSE)
        self.LCD_E.value(False)
        if self.initialising:
            time.sleep_ms(5)
        else:
            time.sleep_us(LCD.E_DELAY)  # 50μs

    def lcd_byte(self, bits, mode):  # Send byte to data pins: bits = data
        self.LCD_RS.value(mode)  # mode = True  for character, False for command
        self.lcd_nybble(bits >> 4)  # send high bits
        self.lcd_nybble(bits)  # then low ones

    def __setitem__(self, line, message):  # Send string to display line 0 or 1
        message = "{0:{1}.{1}}".format(message, self.cols)
        if message != self.lines[line]:  # Only update LCD if data has changed
            self.lines[line] = message  # Update stored line
            self.dirty[line] = True  # Flag its non-correspondence with the LCD device

    def __getitem__(self, line):
        return self.lines[line]

    async def runlcd(self):  # Periodically check for changed text and update LCD if so
        while True:
            for row in range(self.rows):
                if self.dirty[row]:
                    msg = self[row]
                    self.lcd_byte(LCD.LCD_LINES[row], LCD.CMD)
                    for thisbyte in msg:
                        self.lcd_byte(ord(thisbyte), LCD.CHR)
                        await asyncio.sleep_ms(0)  # Reshedule ASAP
                    self.dirty[row] = False
            await asyncio.sleep_ms(20)  # Give other coros a look-in
