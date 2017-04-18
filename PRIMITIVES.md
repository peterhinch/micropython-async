# 1. Synchronisation Primitives

There is often a need to provide synchronisation between coros. A common
example is to avoid what are known as "race conditions" where multiple coros
compete to access a single resource. An example is provided in the ``aswitch.py``
program and discussed in [the docs](./DRIVERS.md). Another hazard is the "deadly
embrace" where two coros wait on the other's completion.

In simple applications these are often addressed with global flags. A more
elegant approach is to use synchronisation primitives. The module ``asyn.py``
offers "micro" implementations of ``Lock``, ``Event``, ``Barrier`` and ``Semaphore``
primitives.

Another synchronisation issue arises with producer and consumer coros. The
producer generates data which the consumer uses. Asyncio provides the ``Queue``
object. The producer puts data onto the queue while the consumer waits for its
arrival (with other coros getting scheduled for the duration). The ``Queue``
guarantees that items are removed in the order in which they were received. As
this is a part of the uasyncio library its use is described in the [tutorial](./TUTORIAL.md).

# 2. Modules

The following modules are provided:
 * ``asyn.py`` The main library.
 * ``asyntest.py`` Test/demo programs for the library.

These modules support CPython 3.5 and MicroPython on Unix and microcontroller
targets. The library is for use only with asyncio. They are ``micro`` in design.
They are not thread safe and should not be used with the ``_thread`` module.

# 3. asyn.py

## 3.1 launch

This function accepts a function or coro as an argument, along with a tuple of
args. If the function is a callback it is executed with the supplied argumets.
If it is a coro, it is scheduled for execution.

args:
 * ``func`` Mandatory. a function or coro. These are provided 'as-is' i.e. not
 using function call syntax.
 * ``tup_args`` Optional. A tuple of arguments, default ``()``. The args are
 upacked when provided to the function.

## 3.1 Lock

This guarantees unique access to a shared resource. The preferred way to use it
is via an asynchronous context manager. In the following code sample a ``Lock``
instance ``lock`` has been created and is passed to all coros wishing to access
the shared resource. Each coro issues the following:

```python
async def bar(lock):
    async with lock:
        # Access resource
```

While the coro ``bar`` is accessing the resource, other coros will pause at the
``async with lock`` statement until the context manager in ``bar()`` is
complete.

### 3.1.1 Definition

Constructor: this takes no arguments.  
Methods:

 * ``locked`` No args. Returns ``True`` if locked.
 * ``release`` No args. Releases the lock.
 * ``acquire`` No args. Coro which pauses until the lock has been acquired. Use
 by executing ``await lock.acquire()``.

## 3.2 Event

This provides a way for one or more coros to pause until another one flags them
to continue. An ``Event`` object is instantiated and passed to all coros using
it. Coros waiting on the event issue ``await event``. Execution pauses
until a coro issues ``event.set()``. ``event.clear()`` must then be issued. An
optional data argument may be passed to ``event.set()`` and retrieved by
``event.value()``.

In the usual case where a single coro is awaiting the event this can be done
immediately after it is received:

```python
async def eventwait(event):
    await event
    event.clear()
```

The coro raising the event may need to check that it has been serviced:

```python
async def foo(event):
    while True:
        # Acquire data from somewhere
        while event.is_set():
            await asyncio.sleep(1) # Wait for coro to respond
        event.set()
```

If multiple coros are to wait on a single event, consider using a ``Barrier``
object described below. This is because the coro which raised the event has no
way to determine whether all others have received it; determining when to clear
it down requires further synchronisation. One way to achieve this is with an
acknowledge event:

```python
async def eventwait(event, ack_event):
    await event
    ack_event.set()
```

Example of this are in ``event_test`` and ``ack_test`` in asyntest.py.

### 3.2.1 Definition

Constructor: takes one optional boolean argument, defaulting False.
 * ``lp`` If ``True`` and the experimental low priority core.py is installed,
 low priority scheduling will be used while awaiting the event. If the standard
 version of uasyncio is installed the arg will have no effect.

Methods:
 * ``set`` Initiates the event. Optional arg ``data``: may be of any type,
 sets the event's value. Default ``None``.
 * ``clear`` No args. Clears the event, sets the value to ``None``.
 * ``is_set`` No args. Returns ``True`` if the event is set.
 * ``value`` No args. Returns the value passed to ``set``.

The optional data value may be used to compensate for the latency in awaiting
the event by passing ``loop.time()``.

## 3.3 Barrier

This enables multiple coros to rendezvous at a particular point. For example
producer and consumer coros can synchronise at a point where the producer has
data available and the consumer is ready to use it. At that point in time the
``Barrier`` can optionally run a callback before releasing the barrier and
allowing all waiting coros to continue.

Constructor.  
Mandatory arg:  
``participants`` The number of coros which will wait on the barrier.  
Optional args:  
``func`` Callback to run. Default ``None``.  
``args`` Tuple of args for the callback. Default ``()``.

The callback can be a function or a coro. In most applications a function is
likely to be used: this can be guaranteed to run to completion beore the
barrier is released.

The ``Barrier`` has no properties or methods for user access. Participant
coros issue ``await my_barrier`` whereupon execution pauses until all other
participants are also waiting on it. At this point any callback will run and
then each participant will re-commence execution. See ``barrier_test`` and
``semaphore_test`` in asyntest.py for example usage.

## 3.4 Semaphore

A semaphore limits the number of coros which can access a resource. It can be
used to limit the number of instances of a particular coro which can run
concurrently. It performs this using an access counter which is initialised by
the constructor and decremented each time a coro acquires the semaphore.

Constructor: Optional arg ``value`` default 1. Number of permitted concurrent
accesses.

Methods:
 * ``release`` No args. Increments the access counter.
 * ``acquire`` No args. Coro. If the access counter is greater than 0,
 decrements it and terminates. Otherwise waits for it to become greater than 0
 before decrementing it and terminating.

The easiest way to use it is with a context manager:

```python
async def foo(sema):
    async with sema:
        # Limited access here
```

There is a difference between a ``Semaphore`` and a ``Lock``. A ``Lock``
instance is owned by the coro which locked it: only that coro can release it. A
``Semaphore`` can be released by any coro which acquired it.

### 3.4.1 BoundedSemaphore

This works identically to the ``Semaphore`` class except that if the ``release``
method causes the access counter to exceed its initial value, a ``ValueError``
is raised.

# 4 asyntest.py

This provides the following test/demo programs. Because ``uasyncio`` retains
state between runs, a soft reset (ctrl-D) should be issued after running a test
and before running another.

 * ``ack_test()`` Use of ``Event`` objects. Runs for 10s.
 * ``event_test()`` Use of ``Lock`` and ``Event`` objects.
 * ``barrier_test()`` Use of the ``Barrier`` class.
 * ``semaphore_test()`` Use of ``Semaphore`` objects. Call with a ``True`` arg
 to demonstrate the ``BoundedSemaphore`` error exception.
