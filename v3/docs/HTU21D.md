# The HTU21D temperature/humidity sensor.

A breakout board is available from
[Sparkfun](https://www.sparkfun.com/products/12064).

This driver was derived from the synchronous Pyboard-specific driver
[here](https://github.com/manitou48/pyboard/blob/master/htu21d.py). It is
designed to be multi-platform and uses `uasyncio` to achieve asynchronous (non-
blocking) operation. The driver maintains `temperature` and `humidity` bound
variables as a non-blocking background task. Consequently reading the values is
effectively instantaneous.

###### [Main README](../README.md)

# Files

 1. `htu21d_mc.py` The asynchronous driver.
 2. `htu_test.py` Test/demo program.

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
async def show_values():
    htu = htu21d_mc.HTU21D(i2c)
    await htu  # Will pause ~120ms
    # Data is now valid
    while True:
        fstr = 'Temp {:5.1f} Humidity {:5.1f}'
        print(fstr.format(htu.temperature, htu.humidity))
        await asyncio.sleep(5)
```

Thermal inertia of the chip packaging means that there is a lag between the
occurrence of a temperature change and the availability of accurate readings.
There is therefore little practical benefit in reducing the `read_delay`.
