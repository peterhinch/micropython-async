# Asynchronous programming in MicroPython

CPython supports asynchronous programming via the `asyncio` library.
MicroPython provides `uasyncio` which is a subset of this, optimised for small
code size and high performance on bare metal targets. This repository provides
documentation, tutorial material and code to aid in its effective use.

# uasyncio version 3

Damien has completely rewritten `uasyncio` which was released as V3.0. See
[PR5332](https://github.com/micropython/micropython/pull/5332). This is now
incorporated in release build V1.13 and subsequent daily builds. 

Resources for V3 may be found in the `v3` directory. These include a guide to
porting applications from V2, an updated tutorial, synchronisation primitives
and various applications and demos.

V2 should now be regarded as obsolete for almost all applications with the
possible exception mentioned below.

### [Go to V3 docs](./v3/README.md)

# uasyncio version 2

The official version 2 is entirely superseded by V3, which improves on it in
every respect.

I produced a modified `fast_io` variant of V2 which is in use for some
specialist purposes. It enables I/O to be scheduled at high priority. Currently
this schedules I/O significantly faster than V3; the maintainers plan to
improve `uasyncio` I/O scheduling. When this is complete I intend to delete all
V2 material.

All V2 resources are in the V2 subdirectory: [see this README](./v2/README.md).
