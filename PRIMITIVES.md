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

###### [Main README](./README.md)

# 2. Modules

The following modules are provided:
 * ``asyn.py`` The main library.
 * ``asyntest.py`` Test/demo programs for the library.

These modules support CPython 3.5 and MicroPython on Unix and microcontroller
targets. The library is for use only with asyncio. They are ``micro`` in design
and are presented as simple, concise examples of asyncio code. They are not
thread safe. Hence they are incompatible with the ``_thread`` module and with
interrupt handlers.

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

## 3.2 Lock

This has now been superceded by the more efficient official version. See the
[test program](https://github.com/micropython/micropython-lib/blob/master/uasyncio.synchro/example_lock.py).
For an example of how to use the preferred official version see [this](./TUTORIAL.md#31-lock).

I have retained this version  in ``asyn.py`` merely as an example of uasyncio
coding. The remainder of this section applies to this version.

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

### 3.2.1 Definition

Constructor: Optional argument ``delay_ms`` default 0. Sets a delay between
attempts to acquire the lock. In applications with coros needing frequent
scheduling a nonzero value will facilitate this at the expense of latency.  
Methods:

 * ``locked`` No args. Returns ``True`` if locked.
 * ``release`` No args. Releases the lock.
 * ``acquire`` No args. Coro which pauses until the lock has been acquired. Use
 by executing ``await lock.acquire()``.

## 3.3 Event

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

### 3.3.1 Definition

Constructor: takes one optional boolean argument, defaulting False.
 * ``lp`` If ``True`` and the experimental low priority core.py is installed,
 low priority scheduling will be used while awaiting the event. If the standard
 version of uasyncio is installed the arg will have no effect.

Synchronous Methods:
 * ``set`` Initiates the event. Optional arg ``data``: may be of any type,
 sets the event's value. Default ``None``.
 * ``clear`` No args. Clears the event, sets the value to ``None``.
 * ``is_set`` No args. Returns ``True`` if the event is set.
 * ``value`` No args. Returns the value passed to ``set``.

The optional data value may be used to compensate for the latency in awaiting
the event by passing ``loop.time()``.

## 3.4 Barrier

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

A special case of `Barrier` usage is where some coros are allowed to pass the
barrier, registering the fact that they have done so. At least one coro must
wait on the barrier. It will continue execution when all non-waiting coros have
passed the barrier, and all other waiting coros have reached it. This can be of
use when cancelling coros. A coro which cancels others might wait until all
cancelled coros have passed the barrier as they quit.

```python
barrier = Barrier(3)  # 3 tasks share the barrier

    # This coro does the cancelling and waits until it is complete.
async def bar():
    # Cancel two tasks
    await barrier
    # Now they have both terminated

    # This coro is capable of being cancelled.
async def foo(n):
    # Cancellable coros must trap the CancelError
    try:
        await forever(n)  # Error propagates up from forever()
    except CancelError:
        print('Instance', n, 'was cancelled')
    finally:
        await barrier(nowait = True)  # Quit immediately
```

Note that `await barrier(nowait = True)` should not be issued in a looping
construct.

## 3.5 Semaphore

A semaphore limits the number of coros which can access a resource. It can be
used to limit the number of instances of a particular coro which can run
concurrently. It performs this using an access counter which is initialised by
the constructor and decremented each time a coro acquires the semaphore.

Constructor: Optional arg ``value`` default 1. Number of permitted concurrent
accesses.

Synchronous method:
 * ``release`` No args. Increments the access counter.

Asynchronous method:
 * ``acquire`` No args. If the access counter is greater than 0, decrements it
 and terminates. Otherwise waits for it to become greater than 0 before
 decrementing it and terminating.

The easiest way to use it is with a context manager:

```python
async def foo(sema):
    async with sema:
        # Limited access here
```

There is a difference between a ``Semaphore`` and a ``Lock``. A ``Lock``
instance is owned by the coro which locked it: only that coro can release it. A
``Semaphore`` can be released by any coro which acquired it.

### 3.5.1 BoundedSemaphore

This works identically to the ``Semaphore`` class except that if the ``release``
method causes the access counter to exceed its initial value, a ``ValueError``
is raised.

## 3.6 NamedCoro

This provides for coros to be readily identified by associating them with a
user-defined name, to enable them to be cancelled or to have an exception
thrown to them. The ``NamedCoro`` class maintains a dict of coros indexed by
the name.

Constructor mandatory args:  
 * ``task`` A coro.
 * `name` Names may be any valid dictionary index. A `ValueError` will be
 raised if the name already exists.

Class methods:  
 * `cancel` Arg: a coro name.
 The named coro will receive a `CancelError` exception the next time it is
 scheduled. The coro should trap this and quit ASAP. `cancel` will return
 `True` if the coro was cancelled or if it had already terminated. It will
 return `False` if the coro is not in the dict or has already been killed.
 * `pend_throw` Args: 1. A coro name 2. An exception.
 The named coro will receive the exception the next time it is scheduled.

Bound variable:
 * `task` This contains the coro and is used to schedule the task using the
 event loop `create_task()` method.

## 3.7 ExitGate

This is obsolete. It was a nasty hack to fake task cancellation at a time when
uasyncio did not support it. The code remains in the module to avoid breaking
existing applications but it will soon be removed.

# 4 asyntest.py

This provides the following test/demo programs. Because ``uasyncio`` retains
state between runs, a soft reset (ctrl-D) should be issued after running a test
and before running another.

 * ``ack_test()`` Use of ``Event`` objects. Runs for 10s.
 * ``event_test()`` Use of ``Lock`` and ``Event`` objects.
 * ``barrier_test()`` Use of the ``Barrier`` class.
 * ``semaphore_test()`` Use of ``Semaphore`` objects. Call with a ``True`` arg
 to demonstrate the ``BoundedSemaphore`` error exception.
 * ``cancel_test1()`` Basic task cancellation.
 * ``cancel_test2()`` Task cacellation with a ``Barrier``.
 * ``cancel_test3()`` Cancellation of a task which has terminated.
