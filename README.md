# Use of MicroPython uasyncio library

This GitHub repository consists of the following parts:
 * Drivers for hardware documented [here](./DRIVERS.md).
 * Synchronisation primitives described [here](./PRIMITIVES.md).
 * An introductory tutorial on asynchronous programming and the use of the
 uasyncio library is offered [here](./TUTORIAL.md). This is a work in progress,
 not least because uasyncio is not yet complete.

# Installation of uasyncio

Firstly install the latest version of ``micropython-uasyncio``. To use queues, also
install the ``micropython-uasyncio.queues`` module.

Instructions on installing library modules may be found [here](https://github.com/micropython/micropython-lib).

On networked hardware, upip may be run locally.

On non-networked hardware the resultant modules will need to be copied to the
target. The above Unix installation will create directories under
``~/.micropython/lib`` which may be copied to the target hardware, either to
the root or to a ``lib`` subdirectory. Alternatively the device may be mounted;
then use the "-p" option to upip to specify the target directory as the mounted
filesystem.

