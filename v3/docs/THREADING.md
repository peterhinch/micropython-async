# Linking uasyncio and other contexts

# 1. Introduction

This document identifies issues arising when `uasyncio` applications interface
code running in a different context. Supported contexts are:
 1. An interrupt service routine (ISR).
 2. Another thread running on the same core.
 3. Code running on a different core (currently only supported on RP2).

Note that hard ISR's require careful coding to avoid RAM allocation. See
[the official docs](http://docs.micropython.org/en/latest/reference/isr_rules.html).
The allocation issue is orthogonal to the concurrency issues discussed in this
document. Concurrency problems apply equally to hard and soft ISR's. Code
samples assume a soft ISR or a function launched by `micropython.schedule`.
[This doc](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/INTERRUPTS.md)
provides specific guidance on interfacing `uasyncio` with ISR's.

The rest of this section compares the characteristics of the three contexts.
Consider this function which updates a global dictionary `d` from a hardware
device. The dictionary is shared with a `uasyncio` task.
```python
def update_dict():
    d["x"] = read_data(0)
    d["y"] = read_data(1)
    d["z"] = read_data(2)
```
This might be called in a soft ISR, in a thread running on the same core as
`uasyncio`, or in a thread running on a different core. Each of these contexts
has different characteristics, outlined below. In all these cases "thread safe"
constructs are needed to interface `uasyncio` tasks with code running in these
contexts. The official `ThreadSafeFlag`, or the classes documented here, may be
used in all of these cases. This function serves to illustrate concurrency
issues: it is not the most effcient way to transfer data.

Beware that some apparently obvious ways to interface an ISR to `uasyncio`
introduce subtle bugs discussed in the doc referenced above. The only reliable
interface is via a thread safe class.

## 1.1 Soft Interrupt Service Routines

 1. The ISR and the main program share a common Python virtual machine (VM).
 Consequently a line of code being executed when the interrupt occurs will run
 to completion before the ISR runs.
 2. An ISR will run to completion before the main program regains control. This
 means that if the ISR updates multiple items, when the main program resumes,
 those items will be mutually consistent. The above code fragment will work
 unchanged.
 3. The fact that ISR code runs to completion means that it must run fast to
 avoid disrupting the main program or delaying other ISR's. ISR code should not
 call blocking routines and should not wait on locks. Item 2. means that locks
 are not usually necessary.
 4. If a burst of interrupts can occur faster than `uasyncio` can schedule the
 handling task, data loss can occur. Consider using a `ThreadSafeQueue`. Note
 that if this high rate is sustained something will break and the overall
 design needs review. It may be necessary to discard some data items.

## 1.2 Threaded code on one core

 1. Both contexts share a common VM so Python code integrity is guaranteed.
 2. If one thread updates a data item there is no risk of the main program
 reading a corrupt or partially updated item. If such code updates multiple
 shared data items, note that `uasyncio` can regain control at any time. The
 above code fragment may not have updated all the dictionary keys when
 `uasyncio` regains control. If mutual consistency is important, a lock or
 `ThreadSafeQueue` must be used.
 3. Code running on a thread other than that running `uasyncio` may block for
 as long as necessary (an application of threading is to handle blocking calls
 in a way that allows `uasyncio` to continue running).

## 1.3 Threaded code on multiple cores

 1. There is no common VM. The underlying machine code of each core runs
 independently.
 2. In the code sample there is a risk of the `uasyncio` task reading the dict
 at the same moment as it is being written. It may read a corrupt or partially
 updated item; there may even be a crash. Using a lock or `ThreadSafeQueue` is
 essential.
 3. Code running on a core other than that running `uasyncio` may block for
 as long as necessary.

A key practical point is that coding errors in synchronising threads can be
hard to locate: consequences can be extremely rare bugs or crashes. It is vital
to be careful in the way that communication between the contexts is achieved. This
doc aims to provide some guidelines and code to assist in this task.

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
problematic if the producer were an ISR. In this case the absence of a lock
would not result in crashes because an ISR cannot interrupt a MicroPython
instruction.

In cases where the duration of a lock is problematic a `ThreadSafeQueue` is
more appropriate as it decouples producer and consumer code.

## 2.1 ThreadSafeQueue

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

### 2.1.1 Blocking

These methods, called with `blocking=False`, produce an immediate return. To
avoid an `IndexError` the user should check for full or empty status before
calling.

The synchronous `get_sync` and `put_sync` methods have blocking modes invoked
by passing `block=True`. Blocking modes are primarily intended for use in the
non-`uasyncio ` context. If invoked in a `uasyncio` task they must not be
allowed to block because it would lock up the scheduler. Nor should they be
allowed to block in an ISR where blocking can have unpredictable consequences.

### 2.1.2 Object ownership

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
finished with the item. In general it is simpler to create new objects and let
the MicroPython garbage collector delete them as per the first sample.

### 2.1.3 A complete example

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
# 3. Synchronisation

The principal means of synchronising `uasyncio` code with that running in
another context is the `ThreadsafeFlag`. This is discussed in the
[official docs](http://docs.micropython.org/en/latest/library/uasyncio.html#class-threadsafeflag)
and [tutorial](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#36-threadsafeflag).
In essence a single `uasyncio` task waits on a shared `ThreadSafeEvent`. Code
running in another context sets the flag. When the scheduler regains control
and other pending tasks have run, the waiting task resumes.

## 3.1 Threadsafe Event

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
