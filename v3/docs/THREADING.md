# Linking uasyncio and other contexts

# 1. Introduction

This document identifies issues arising when `uasyncio` applications interface
code running in a different context. Supported contexts are:
 1. An interrupt service routine (ISR).
 2. Another thread running on the same core.
 3. Code running on a different core (currently only supported on RP2).

The first two cases are relatively straightforward because both contexts share
a common bytecode interpreter and GIL. There is a guarantee that even a hard
MicroPython (MP) ISR will not interrupt execution of a line of Python code.

This is not the case where the threads run on different cores, where there is
no synchronisation between the streams of machine code. If the two threads
concurrently modify a shared Python object it is possible that corruption will
occur. Reading an object while it is being written can also produce an
unpredictable outcome.

A key practical point is that coding errors can be hard to identify: the
consequences can be extremely rare bugs or crashes.

There are two fundamental problems: data sharing and synchronisation.

# 2. Data sharing

The simplest case is a shared pool of data. It is possible to share an `int` or
`bool` because at machine code level writing an `int` is "atomic": it cannot be
interrupted. Anything more complex must be protected to ensure that concurrent
access cannot take place. The consequences even of reading an object while it
is being written can be unpredictable. One approach is to use locking:

```python
lock = _thread.allocate_lock()
values = { "X": 0, "Y": 0, "Z": 0}
def producer():
    while True:
        lock.acquire()
        values["X"] = sensor_read(0)
        values["Y"] = sensor_read(1)
        values["Z"] = sensor_read(2)
        lock.release()
        time.sleep_ms(100)

_thread.start_new_thread(producer, ())

async def consumer():
    while True:
        lock.acquire()
        await process(values)  # Do something with the data
        lock.release()
```
This will work even for the multi core case. However the consumer might hold
the lock for some time: it will take time for the scheduler to execute the
`process()` call, and the call itself will take time to run. This would be
problematic if the producer were an ISR.

In cases such as this a `ThreadSafeQueue` is more appropriate as it decouples
producer and consumer code.

# 2. Threadsafe Event

The `ThreadsafeFlag` has a limitation in that only a single task can wait on
it. The `ThreadSafeEvent` overcomes this. It is subclassed from `Event` and
presents the same interface. The `set` method may be called from an ISR or from
code running on another core. Any number of tasks may wait on it.

The following Pyboard-specific code demos its use in a hard ISR:
```python
import uasyncio as asyncio
from threadsafe import ThreadSafeEvent
from pyb import Timer

async def waiter(n, evt):
    try:
        await evt.wait()
        print(f"Waiter {n} got event")
    except asyncio.CancelledError:
        print(f"Waiter {n} cancelled")

async def can(task):
    await asyncio.sleep_ms(100)
    task.cancel()

async def main():
    evt = ThreadSafeEvent()
    tim = Timer(4, freq=1, callback=lambda t: evt.set())
    nt = 0
    while True:
        tasks = [asyncio.create_task(waiter(n + 1, evt)) for n in range(4)]
        asyncio.create_task(can(tasks[nt]))
        await asyncio.gather(*tasks, return_exceptions=True)
        evt.clear()
        print("Cleared event")
        nt = (nt + 1) % 4

asyncio.run(main())
```

# 3. Threadsafe Queue

This queue is designed to interface between one `uasyncio` task and a single
thread running in a different context. This can be an interrupt service routine
(ISR), code running in a different thread or code on a different core.

Any Python object may be placed on a `ThreadSafeQueue`. If bi-directional
communication is required between the two contexts, two `ThreadSafeQueue`
instances are required.

Attributes of `ThreadSafeQueue`:
 1. It is of fixed capacity defined on instantiation.
 2. It uses a pre-allocated buffer of user selectable type (`Queue` uses a
 dynaically allocated `list`).
 3. It is an asynchronous iterator allowing retrieval with `async for`.
 4. It provides synchronous "put" and "get" methods. If the queue becomes full
 (put) or empty (get), behaviour is user definable. The method either blocks or
 raises an `IndexError`.

Constructor mandatory arg:
 * `buf` Buffer for the queue, e.g. list `[0 for _ in range(20)]` or array. A
 buffer of size `N` can hold a maximum of `N-1` items.

Synchronous methods.  
 * `qsize` No arg. Returns the number of items in the queue.
 * `empty` No arg. Returns `True` if the queue is empty.
 * `full` No arg. Returns `True` if the queue is full.
 * `get_sync` Arg `block=False`. Returns an object from the queue. Raises
 `IndexError` if the queue is empty, unless `block==True` in which case the
 method blocks until the `uasyncio` tasks put an item on the queue.
 * `put_sync` Args: the object to put on the queue, `block=False`. Raises
 `IndexError` if the  queue is full unless `block==True` in which case the
 method blocks until the `uasyncio` tasks remove an item from the queue.

See the note below re blocking methods.

Asynchronous methods:  
 * `put` Arg: the object to put on the queue. If the queue is full, it will
 block until space is available.
 * `get` No arg. Returns an object from the queue. If the queue is empty, it
 will block until an object is put on the queue. Normal retrieval is with
 `async for` but this method provides an alternative.


In use as a data consumer the `uasyncio` code will use `async for` to retrieve
items from the queue. If it is a data provider it will use `put` to place
objects on the queue.

Data consumer:
```python
async def handle_queued_data(q):
    async for obj in q:
        # Process obj
```
Data provider:
```python
async def feed_queue(q):
    while True:
        data = await data_source()
        await q.put(data)
```
The alternate thread will use synchronous methods.

Data provider (throw if full):
```python
while True:
    data = data_source()
    try:
        q.put_sync(data)
    except IndexError:
        # Queue is full
```
Data consumer (block while empty):
```python
while True:
    data = q.get(block=True)  # May take a while if the uasyncio side is slow
    process(data)  # Do something with it
```

## 3.1 Blocking

These methods, called with `blocking=False`, produce an immediate return. To
avoid an `IndexError` the user should check for full or empty status before
calling.

The synchronous `get_sync` and `put_sync` methods have blocking modes invoked
by passing `block=True`. Blocking modes are primarily intended for use in the
non-`uasyncio ` context. If invoked in a `uasyncio` task they must not be
allowed to block because it would lock up the scheduler. Nor should they be
allowed to block in an ISR where blocking can have unpredictable consequences.

## 3.2 Object ownership

Any Python object can be placed on a queue, but the user should be aware that
once the producer puts an object on the queue it loses ownership of the object
until the consumer has finished using it. In this sample the producer reads X,
Y and Z values from a sensor, puts them in a list or array and places the
object on a queue:
```python
def get_coordinates(q):
    while True:
        lst = [axis(0), axis(1), axis(2)]  # Read sensors and put into list
        putq.put_sync(lst, block=True)
```
This is valid because a new list is created each time. The following will not
work:
```python
def get_coordinates(q):
    a = array.array("I", (0,0,0))
    while True:
        a[0], a[1], a[2] = [axis(0), axis(1), axis(2)]
        putq.put_sync(lst, block=True)
```
The problem here is that the array is modified after being put on the queue. If
the queue is capable of holding 10 objects, 10 array instances are required. Re
using objects requires the producer to be notified that the consumer has
finished with the item.

## 3.3 A complete example

This demonstrates an echo server running on core 2. The `sender` task sends
consecutive integers to the server, which echoes them back on a second queue.
```python
import uasyncio as asyncio
from threadsafe import ThreadSafeQueue
import _thread
from time import sleep_ms

def core_2(getq, putq):  # Run on core 2
    buf = []
    while True:
        while getq.qsize():  # Ensure no exception when queue is empty
            buf.append(getq.get_sync())
        for x in buf:
            putq.put_sync(x, block=True)  # Wait if queue fills.
        buf.clear()
        sleep_ms(30)
        
async def sender(to_core2):
    x = 0
    while True:
        await to_core2.put(x := x + 1)

async def main():
    to_core2 = ThreadSafeQueue([0 for _ in range(10)])
    from_core2 = ThreadSafeQueue([0 for _ in range(10)])
    _thread.start_new_thread(core_2, (to_core2, from_core2))
    asyncio.create_task(sender(to_core2))
    n = 0
    async for x in from_core2:
        if not x % 1000:
            print(f"Received {x} queue items.")
        n += 1
        assert x == n

asyncio.run(main())
```
