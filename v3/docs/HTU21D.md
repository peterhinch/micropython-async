# The HTU21D temperature/humidity sensor.

Breakout boards are available from
[Adafruit](https://www.adafruit.com/product/1899).

This [Sparkfun board](https://www.sparkfun.com/products/13763) has an Si7021
chip which, from a look at the datasheet, appears to be a clone of the HTU21D.
The Sparkfun prduct ID is the same as boards which I own: mine have HTU21D
chips.

This driver was derived from the synchronous Pyboard-specific driver
[here](https://github.com/manitou48/pyboard/blob/master/htu21d.py). It is
designed to be multi-platform and uses `uasyncio` to achieve asynchronous (non-
blocking) operation. The driver maintains `temperature` and `humidity` bound
variables as a non-blocking background task. Consequently reading the values is
effectively instantaneous.

###### [Main V3 README](../README.md)

# Installation

Copy the `as_drivers/htu21d` directory and contents to the target hardware.
Copy `primitives` and contents to the target.

Files:  
 1. `htu21d_mc.py` The asynchronous driver.
 2. `htu_test.py` Test/demo program.

# The test script

This runs on any Pyboard or ESP32. for other platforms pin numbers will need to
be changed. 

| Pin  | Pyboard | ESP32 |
|:----:|:-------:|:-----:|
| gnd  |  gnd    |  gnd  |
| Vin  |  3V3    |  3V3  |
| scl  |  X9     |  22   |
| sda  |  X10    |  23   |

On the Pyboard D the 3.3V supply must be enabled with
```python
machine.Pin.board.EN_3V3.value(1)
```
This also enables the I2C pullups on the X side. To run the demo issue:
```python
import as_drivers.htu21d.htu_test
```

# The driver

This provides a single class `HTU21D`.

Constructor.  
This takes two args, `i2c` (mandatory) and an optional `read_delay=10`. The
former must be an initialised I2C bus instance. The `read_delay` (secs)
determines how frequently the data values are updated.

Public bound values
 1. `temperature` Latest value in Celcius.
 2. `humidity` Latest value of relative humidity (%).

Initial readings will not be complete until about 120ms after the class is
instantiated. Prior to this the values will be `None`. To avoid such invalid
readings the class is awaitable and may be used as follows.

```python
import uasyncio as asyncio
from machine import Pin, I2C
from as_drivers.htu21d import HTU21D

htu = HTU21D(I2C(1))  # Pyboard scl=X9 sda=X10

async def main():
    await htu  # Wait for device to be ready
    while True:
        fstr = 'Temp {:5.1f} Humidity {:5.1f}'
        print(fstr.format(htu.temperature, htu.humidity))
        await asyncio.sleep(5)

asyncio.run(main())
```

Thermal inertia of the chip packaging means that there is a lag between the
occurrence of a temperature change and the availability of accurate readings.
There is therefore little practical benefit in reducing the `read_delay`.
