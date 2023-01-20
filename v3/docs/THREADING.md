# Linking uasyncio and other contexts

This document is primarily for those wishing to interface `uasyncio` code with
that running under the `_thread` module. It presents classes for that purpose
which may also find use for communicating between threads and in interrupt
service routine (ISR) applications. It provides an overview of the problems
implicit in pre-emptive multi tasking.

It is not an introduction into ISR coding. For this see
[the official docs](http://docs.micropython.org/en/latest/reference/isr_rules.html)
and [this doc](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/INTERRUPTS.md)
which provides specific guidance on interfacing `uasyncio` with ISR's.

Because of [this issue](https://github.com/micropython/micropython/issues/7965)
the `ThreadSafeFlag` class does not work under the Unix build. The classes
presented here depend on this: none can be expected to work on Unix until this
is fixed.

###### [Main README](../README.md)
###### [Tutorial](./TUTORIAL.md)

# Contents

 1. [Introduction](./THREADING.md#1-introduction) The various types of pre-emptive code.  
  1.1 [Hard Interrupt Service Routines](./THREADING.md#11-hard-interrupt-service-routines)  
  1.2 [Soft Interrupt Service Routines](./THREADING.md#12-soft-interrupt-service-routines) Also code scheduled by micropython.schedule()  
  1.3 [Threaded code on one core](./THREADING.md#13-threaded-code-on-one-core)  
  1.4 [Threaded code on multiple cores](./THREADING.md#14-threaded-code-on-multiple-cores)  
  1.5 [Globals](./THREADING.md#15-globals)  
  1.6 [Debugging](./THREADING.md#16-debugging)  
 2. [Sharing data](./THREADING.md#2-sharing-data)  
  2.1 [A pool](./THREADING.md#21-a-pool) Sharing a set of variables.  
  2.2 [ThreadSafeQueue](./THREADING.md#22-threadsafequeue)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.2.1 [Blocking](./THREADING.md#221-blocking)  
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.2.3 [Object ownership](./THREADING.md#223-object-ownership)  
 3. [Synchronisation](./THREADING.md#3-synchronisation)  
  3.1 [Threadsafe Event](./THREADING.md#31-threadsafe-event)  
  3.2 [Message](./THREADING.md#32-message) A threadsafe event with data payload.  
 4. [Taming blocking functions](./THREADING.md#4-taming-blocking-functions)  
 5. [Glossary](./THREADING.md#5-glossary) Terminology of realtime coding.  

# 1. Introduction

Various issues arise when `uasyncio` applications interface with code running
in a different context. Supported contexts are:
 1. A hard interrupt service routine (ISR).
 2. A soft ISR. This includes code scheduled by `micropython.schedule()`.
 3. Another thread running on the same core.
 4. Code running on a different core (currently only supported on RP2).

In all these cases the contexts share a common VM (the virtual machine which
executes Python bytecode). This enables the contexts to share global state. The
contexts differ in their use of the GIL [see glossary](./THREADING.md#5-glossary).

This section compares the characteristics of the four contexts. Consider this
function which updates a global dictionary `d` from a hardware device. The
dictionary is shared with a `uasyncio` task. (The function serves to illustrate
concurrency issues: it is not the most effcient way to transfer data.)
```python
def update_dict():
    d["x"] = read_data(0)
    d["y"] = read_data(1)
    d["z"] = read_data(2)
```
This might be called in a hard or soft ISR, in a thread running on the same
core as `uasyncio`, or in a thread running on a different core. Each of these
contexts has different characteristics, outlined below. In all these cases
"thread safe" constructs are needed to interface `uasyncio` tasks with code
running in these contexts. The official `ThreadSafeFlag`, or the classes
documented here, may be used.

Beware that some apparently obvious ways to interface an ISR to `uasyncio`
introduce subtle bugs discussed in
[this doc](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/INTERRUPTS.md)
referenced above. The only reliable interface is via a thread safe class,
usually `ThreadSafeFlag`.

## 1.1 Hard Interrupt Service Routines

 1. The ISR sees the GIL state of the main program: if the latter has locked
 the GIL, the ISR will still run. This renders the GIL, as seen by the ISR,
 ineffective. Built in Python objects (`list`, `dict` etc.) will not be
 corrupted if an ISR runs while the object's contents are being modified as
 these updates are atomic. This guarantee is limited: the code will not crash,
 but there may be consistency problems. See **consistency** below. The lack of GIL
 functionality means that failure can occur if the object's _structure_ is
 modified, for example by the main program adding or deleting a dictionary
 entry. This results in issues for [globals](./THREADING.md#15-globals).
 2. An ISR will run to completion before the main program regains control. This
 means that if the ISR updates multiple items, when the main program resumes,
 those items will be mutually consistent. The above code fragment will provide
 mutually consistent data (but see **consistency** below).
 3. The fact that ISR code runs to completion means that it must run fast to
 avoid disrupting the main program or delaying other ISR's. ISR code should not
 call blocking routines. It should not wait on locks because there is no way
 for the interrupted code to release the lock. See locks below.
 4. If a burst of interrupts can occur faster than `uasyncio` can schedule the
 handling task, data loss can occur. Consider using a `ThreadSafeQueue`. Note
 that if this high rate is sustained something will break: the overall design
 needs review. It may be necessary to discard some data items.

#### locks

There is a valid case where a hard ISR checks the status of a lock, aborting if
the lock is set.

#### consistency

Consider this code fragment:
```python
a = [0, 0, 0]
b = [0, 0, 0]
def hard_isr():
    a[0] = read_data(0)
    b[0] = read_data(1)

async def foo():
    while True:
        await process(a + b)
```
A hard ISR can occur during the execution of a bytecode. This means that the
combined list passed to `process()` might comprise old a + new b. Even though
the ISR produces consistent data, the fact that it can preempt the main code
at any time means that to read consistent data interrupts must be disabled:
```python
async def foo():
    while True:
        state = machine.disable_irq()
        d = a + b  # Disable for as short a time as possible
        machine.enable_irq(state)
        await process(d)
```

## 1.2 Soft Interrupt Service Routines 

This also includes code scheduled by `micropython.schedule()` which is assumed
to have been called from a hard ISR.

 1. A soft ISR can only run at certain bytecode boundaries, not during
 execution of a bytecode. It cannot interrupt garbage collection; this enables
 soft ISR code to allocate.
 2. As per hard ISR's.
 3. A soft ISR should still be designed to complete quickly. While it won't
 delay hard ISR's it nevertheless pre-empts the main program. In principle it
 can wait on a lock, but only if the lock is released by a hard ISR or another
 hard context (a thread or code on another core).
 4. As per hard ISR's.

## 1.3 Threaded code on one core

 1. The common GIL ensures that built-in Python objects (`list`, `dict` etc.)
 will not be corrupted if a read on one thread occurs while the object's
 contents or the object's structure are being updated.
 2. This protection does not extend to user defined data structures. The fact
 that a dictionary won't be corrupted by concurrent access does not imply that
 its contents will be mutually consistent. In the code sample in section 1, if
 the application needs mutual consistency between the dictionary values, a lock
 is needed to ensure that a read cannot be scheduled while an update is in
 progress.
 3. The above means that, for example, calling `uasyncio.create_task` from a
 thread is unsafe as it can destroy the mutual consistency of `uasyncio` data
 structures.
 4. Code running on a thread other than that running `uasyncio` may block for
 as long as necessary (an application of threading is to handle blocking calls
 in a way that allows `uasyncio` to continue running).

## 1.4 Threaded code on multiple cores

Currently this applies to RP2 and Unix ports, although as explained above the
thread safe classes offered here do not yet support Unix.

 1. There is no common GIL. This means that under some conditions Python built
 in objects can be corrupted.
 2. In the code sample there is a risk of the `uasyncio` task reading the dict
 at the same moment as it is being written. Updating a dictionary data entry is
 atomic: there is no risk of corrupt data being read. In the code sample a lock
 is only required if mutual consistency of the three values is essential.
 3. In the absence of a GIL some operations on built-in objects are not thread
 safe. For example adding or deleting items in a `dict`. This extends to global
 variables which are implemented as a `dict`. See [Globals](./THREADING.md#15-globals).
 4. The observations in 1.3 re user defined data structures and `uasyncio`
 interfacing apply.
 5. Code running on a core other than that running `uasyncio` may block for
 as long as necessary.

[See this reference from @jimmo](https://github.com/orgs/micropython/discussions/10135#discussioncomment-4309865).

## 1.5 Globals

Globals are implemented as a `dict`. Adding or deleting an entry is unsafe in
the main program if there is a context which accesses global data and does not
use the GIL. This means hard ISR's and code running on another core. Given that
shared global data is widely used, the following guidelines should be followed.

All globals should be declared in the main program before an ISR starts to run,
and before code on another core is started. It is valid to insert placeholder
data, as updates to `dict` data are atomic. In the example below, a pointer to
the `None` object is replaced by a pointer to a class instance: a pointer
update is atomic so can occur while globals are accessed by code in other
contexts.
```python
display_driver = None
# Start code on other core
# It's now valid to do
display_driver = DisplayDriverClass(args)
```
The hazard with globals can occur in other ways. Importing a module while other
contexts are accessing globals can be problematic as that module might create
global objects. The following would present a hazard if `foo` were run for the
first time while globals were being accessed:
```python
def foo():
    global bar
    bar = 42
```
Once again the hazard is avoided by, in global scope, populating `bar` prior
with a placeholder before allowing other contexts to run.

If globals must be created and destroyed dynaically, a lock must be used.

## 1.6 Debugging

A key practical point is that coding errors in synchronising threads can be
hard to locate: consequences can be extremely rare bugs or (in the case of 
multi-core systems) crashes. It is vital to be careful in the way that
communication between the contexts is achieved. This doc aims to provide some
guidelines and code to assist in this task.

There are two fundamental problems: data sharing and synchronisation.

###### [Contents](./THREADING.md#contents)

# 2. Sharing data

## 2.1 A pool

The simplest case is a shared pool of data. It is possible to share an `int` or
`bool` because at machine code level writing an `int` is "atomic": it cannot be
interrupted. A shared global `dict` might be replaced in its entirety by one
process and read by another. This is safe because the shared variable is a
pointer, and replacing a pointer is atomic. Problems arise when multiple fields
are updated by one process and read by another, as the read might occur while
the write operation is in progress.

One approach is to use locking. This example solves data sharing, but does not
address synchronisation:
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
        await asyncio.sleep_ms(0)  # Ensure producer has time to grab the lock
```
Condsider also this code:
```python
def consumer():
    send(d["x"].height())  # d is a global dict
    send(d["x"].width())  # d["x"] is an instance of a class
```
In this instance if the producer, running in a different context, changes
`d["x"]` between the two `send()` calls, different objects will be accessed. A
lock should be used.

Locking is recommended where the producer runs in a different thread from
`uasyncio`. However the consumer might hold the lock for some time: in the
first sample it will take time for the scheduler to execute the `process()`
call, and the call itself will take time to run. In cases where the duration
of a lock is problematic a `ThreadSafeQueue` is more appropriate than a locked
pool as it decouples producer and consumer code.

As stated above, if the producer is an ISR a lock is normally unusable.
Producer code would follow this pattern:
```python
values = { "X": 0, "Y": 0, "Z": 0}
def producer():
    values["X"] = sensor_read(0)
    values["Y"] = sensor_read(1)
    values["Z"] = sensor_read(2)
```
and the ISR would run to completion before `uasyncio` resumed. However the ISR
might run while the `uasyncio` task was reading the values: to ensure mutual
consistency of the dict values the consumer should disable interrupts while the
read is in progress.

###### [Contents](./THREADING.md#contents)

## 2.2 ThreadSafeQueue

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

###### [Contents](./THREADING.md#contents)

### 2.2.1 Blocking

These methods, called with `blocking=False`, produce an immediate return. To
avoid an `IndexError` the user should check for full or empty status before
calling.

The synchronous `get_sync` and `put_sync` methods have blocking modes invoked
by passing `block=True`. Blocking modes are primarily intended for use in the
non-`uasyncio ` context. If invoked in a `uasyncio` task they must not be
allowed to block because it would lock up the scheduler. Nor should they be
allowed to block in an ISR where blocking can have unpredictable consequences.

###### [Contents](./THREADING.md#contents)

### 2.2.2 Object ownership

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

###### [Contents](./THREADING.md#contents)

### 2.2.3 A complete example

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
###### [Contents](./THREADING.md#contents)

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
## 3.2 Message

The `Message` class uses [ThreadSafeFlag](./TUTORIAL.md#36-threadsafeflag) to
provide an object similar to `Event` with the following differences:

 * `.set()` has an optional data payload.
 * `.set()` can be called from another thread, another core, or from an ISR.
 * It is an awaitable class.
 * Payloads may be retrieved in an asynchronous iterator.
 * Multiple tasks can wait on a single `Message` instance.

Constructor:
 * No args.

Synchronous methods:
 * `set(data=None)` Trigger the `Message` with optional payload (may be any
 Python object).
 * `is_set()` Returns `True` if the `Message` is set, `False` if `.clear()` has
 been issued.
 * `clear()` Clears the triggered status. At least one task waiting on the
 message should issue `clear()`.
 * `value()` Return the payload.

Asynchronous Method:
 * `wait()` Pause until message is triggered. You can also `await` the message
 as per the examples.

The `.set()` method can accept an optional data value of any type. The task
waiting on the `Message` can retrieve it by means of `.value()` or by awaiting
the `Message` as below. A `Message` can provide a means of communication from
an interrupt handler and a task. The handler services the hardware and issues
`.set()` which causes the waiting task to resume (in relatively slow time).

This illustrates basic usage:
```python
import uasyncio as asyncio
from threadsafe import Message

async def waiter(msg):
    print('Waiting for message')
    res = await msg
    print('waiter got', res)
    msg.clear()

async def main():
    msg = Message()
    asyncio.create_task(waiter(msg))
    await asyncio.sleep(1)
    msg.set('Hello')  # Optional arg
    await asyncio.sleep(1)

asyncio.run(main())
```
The following example shows multiple tasks awaiting a `Message`.
```python
from threadsafe import Message
import uasyncio as asyncio

async def bar(msg, n):
    while True:
        res = await msg
        msg.clear()
        print(n, res)
        # Pause until other coros waiting on msg have run and before again
        # awaiting a message.
        await asyncio.sleep_ms(0)

async def main():
    msg = Message()
    for n in range(5):
        asyncio.create_task(bar(msg, n))
    k = 0
    while True:
        k += 1
        await asyncio.sleep_ms(1000)
        msg.set('Hello {}'.format(k))

asyncio.run(main())
```
Receiving messages in an asynchronous iterator:
```python
import uasyncio as asyncio
from threadsafe import Message

async def waiter(msg):
    async for text in msg:
        print(f"Waiter got {text}")
        msg.clear()

async def main():
    msg = Message()
    task = asyncio.create_task(waiter(msg))
    for text in ("Hello", "This is a", "message", "goodbye"):
        msg.set(text)
        await asyncio.sleep(1)
    task.cancel()
    await asyncio.sleep(1)
    print("Done")

asyncio.run(main())
```
The `Message` class does not have a queue: if the instance is set, then set
again before it is accessed, the first data item will be lost.

###### [Contents](./THREADING.md#contents)

# 4. Taming blocking functions

Blocking functions or methods have the potential of stalling the `uasyncio`
scheduler. Short of rewriting them to work properly the only way to tame them
is to run them in another thread. The following is a way to achieve this.
```python
async def unblock(func, *args, **kwargs):
    def wrap(func, message, args, kwargs):
        message.set(func(*args, **kwargs))  # Run the blocking function.
    msg = Message()
    _thread.start_new_thread(wrap, (func, msg, args, kwargs))
    return await msg
```
Given a blocking function `blocking` taking two positional and two keyword args
it may be awaited in a `uasyncio` task with
```python
    res = await unblock(blocking, 1, 2, c = 3, d = 4)
```
The function runs "in the background" with other tasks running; only the
calling task is paused. Note how the args are passed. There is a "gotcha" which
is cancellation. It is not valid to cancel the `unblock` task because the
underlying thread will still be running. There is no general solution to this.
If the specific blocking function has a means of interrupting it or of forcing
a timeout then it may be possible to code a solution.

The following is a complete example where blocking is demonstrated with
`time.sleep`.
```python
import uasyncio as asyncio
from threadsafe import Message
import _thread
from time import sleep

def slow_add(a, b, *, c, d):  # Blocking function.
    sleep(5)
    return a + b + c + d

# Convert a blocking function to a nonblocking one using threading.
async def unblock(func, *args, **kwargs):
    def wrap(func, message, args, kwargs):
        message.set(func(*args, **kwargs))  # Run the blocking function.
    msg = Message()
    _thread.start_new_thread(wrap, (func, msg, args, kwargs))
    return await msg

async def busywork():  # Prove uasyncio is running.
    while True:
        print("#", end="")
        await asyncio.sleep_ms(200)

async def main():
    bw = asyncio.create_task(busywork())
    res = await unblock(slow_add, 1, 2, c = 3, d = 4)
    bw.cancel()
    print(f"\nDone. Result = {res}")

asyncio.run(main())
```
###### [Contents](./THREADING.md#contents)

# 5. Glossary

### ISR

An Interrupt Service Routine: code that runs in response to an interrupt. Hard
ISR's offer very low latency but require careful coding - see
[official docs](http://docs.micropython.org/en/latest/reference/isr_rules.html).

### Context

In MicroPython terms a `context` may be viewed as a stream of bytecodes. A
`uasyncio` program comprises a single context: execution is passed between
tasks and the scheduler as a single stream of code. By contrast code in an ISR
can preempt the main stream to run its own stream. This is also true of threads
which can preempt each other at arbitrary times, and code on another core
which runs independently albeit under the same VM.

### GIL

MicroPython has a Global Interpreter Lock. The purpose of this is to ensure
that multi-threaded programs cannot cause corruption in the event that two
contexts simultaneously modify an instance of a Python built-in class. It does
not protect user defined objects.

### micropython.schedule

The relevance of this is that it is normally called in a hard ISR. In this
case the scheduled code runs in a different context to the main program. See
[official docs](http://docs.micropython.org/en/latest/library/micropython.html#micropython.schedule).

### VM

In MicroPython terms a VM is the Virtual Machine that executes bytecode. Code
running in different contexts share a common VM which enables the contexts to
share global objects.

### Atomic

An operation is described as "atomic" if it can be guaranteed to proceed to
completion without being preempted. Writing an integer is atomic at the machine
code level. Updating a dictionary value is atomic at bytecode level. Adding or
deleting a dictionary key is not.
