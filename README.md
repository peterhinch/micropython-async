# Asynchronous programming in MicroPython

CPython supports asynchronous programming via the `asyncio` library.
MicroPython provides `asyncio` which is a subset of this, optimised for small
code size and high performance on bare metal targets. This repository provides
documentation, tutorial material and code to aid in its effective use.

# asyncio version 3

Damien has completely rewritten `asyncio` which was released as V3.0. This is
incorporated in all recent firmware builds. The resources in this repo may be found in the
`v3` directory. These include a tutorial, synchronisation primitives, drivers,
applications and demos.

# Concurrency

Other documents provide hints on asynchronous programming techniques including
threading and multi-core coding.

### [Go to V3 docs](./v3/README.md)

# uasyncio version 2

This is obsolete: code and docs have been removed.
