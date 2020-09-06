# 1. Driver for character-based LCD displays

This driver is for displays based on the Hitachi HD44780 driver: these are
widely available, typically in 16 character x 2 rows format.

###### [Main README](../README.md)

# 2. Files

 * `alcd.py` Driver, includes connection details.
 * `alcdtest.py` Test/demo script.

# 3. Typical wiring

The driver uses 4-bit mode to economise on pins and wiring. Pins are arbitrary
but this configuration was used in testing:

| LCD  |Board |
|:----:|:----:|
|  Rs  |  Y1  |
|  E   |  Y2  |
|  D7  |  Y3  |
|  D6  |  Y4  |
|  D5  |  Y5  |
|  D4  |  Y6  |

# 4. LCD Class

## 4.1 Constructor

This takes the following positional args:
 * `pinlist` A tuple of 6 strings, being the Pyboard pins used for signals
 `Rs`, `E`, `D4`, `D5`, `D6`, `D7` e.g. `('Y1','Y2','Y6','Y5','Y4','Y3')`.
 * `cols` The number of horizontal characters in the display (typically 16).
 * `rows` Default 2. Number of rows in the display.

## 4.2 Display updates

The class has no public properties or methods. The display is represented as an
array of strings indexed by row. The row contents is replaced in its entirety,
replacing all previous contents regardless of length. This is illustrated by
the test program:

```python
import uasyncio as asyncio
import utime as time
from alcd import LCD, PINLIST

lcd = LCD(PINLIST, cols = 16)

async def lcd_task():
    for secs in range(20, -1, -1):
        lcd[0] = 'MicroPython {}'.format(secs)
        lcd[1] = "{:11d}uS".format(time.ticks_us())
        await asyncio.sleep(1)

loop = asyncio.get_event_loop()
loop.run_until_complete(lcd_task())
```

The row contents may be read back by issuing

```python
row0 = lcd[0]
```

# 5. Display Formatting

The driver represents an LCD display as an array indexed by row. Assigning a
string to a row causes that row to be updated. To write text to a specific
column of the display it is recommended to use the Python string `format`
method.

For example this function formats a string such that it is left-padded with
spaces to a given column and right-padded to the specified width (typically the
width of the display). Right padding is not necessary but is included to
illustrate how right-justified formatting can be achieved:

```python
def print_at(st, col, width=16):
    return '{:>{col}s}{:{t}s}'.format(st,'', col=col+len(st), t = width-(col+len(st)))
```

```
>>> print_at('cat', 2)
'  cat           '
>>> len(_)
16
>>> 
```

This use of the `format` method may be extended to achieve more complex
tabulated data layouts.
