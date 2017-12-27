# 1. Synchronisation Primitives

There is often a need to provide synchronisation between coros. A common
example is to avoid what are known as "race conditions" where multiple coros
compete to access a single resource. An example is provided in the `aswitch.py`
program and discussed in [the docs](./DRIVERS.md). Another hazard is the "deadly
embrace" where two coros wait on the other's completion.

In simple applications these are often addressed with global flags. A more
elegant approach is to use synchronisation primitives. The module `asyn.py`
offers "micro" implementations of `Lock`, `Event`, `Barrier` and `Semaphore`
primitives.

Another synchronisation issue arises with producer and consumer coros. The
producer generates data which the consumer uses. Asyncio provides the `Queue`
object. The producer puts data onto the queue while the consumer waits for its
arrival (with other coros getting scheduled for the duration). The `Queue`
guarantees that items are removed in the order in which they were received. As
this is a part of the uasyncio library its use is described in the [tutorial](./TUTORIAL.md).

**NOTE** The support for task cancellation is under development. The API has
changed and may change further.

###### [Main README](./README.md)

# 2. Modules

The following modules are provided:
 * `asyn.py` The main library.
 * `asyntest.py` Test/demo programs for the library.

These modules support CPython 3.5 and MicroPython on Unix and microcontroller
targets. The library is for use only with asyncio. They are `micro` in design
and are presented as simple, concise examples of asyncio code. They are not
thread safe. Hence they are incompatible with the `_thread` module and with
interrupt handlers.

# 3. asyn.py

## 3.1 launch

This function accepts a function or coro as an argument, along with a tuple of
args. If the function is a callback it is executed with the supplied argumets.
If it is a coro, it is scheduled for execution.

args:
 * `func` Mandatory. a function or coro. These are provided 'as-is' i.e. not
 using function call syntax.
 * `tup_args` Optional. A tuple of arguments, default `()`. The args are
 upacked when provided to the function.

## 3.2 Lock

This has now been superceded by the more efficient official version. See the
[test program](https://github.com/micropython/micropython-lib/blob/master/uasyncio.synchro/example_lock.py).
For an example of how to use the preferred official version see [this](./TUTORIAL.md#31-lock).

I have retained this version  in `asyn.py` merely as an example of uasyncio
coding. The remainder of this section applies to this version.

This guarantees unique access to a shared resource. The preferred way to use it
is via an asynchronous context manager. In the following code sample a `Lock`
instance `lock` has been created and is passed to all coros wishing to access
the shared resource. Each coro issues the following:

```python
async def bar(lock):
    async with lock:
        # Access resource
```

While the coro `bar` is accessing the resource, other coros will pause at the
`async with lock` statement until the context manager in `bar()` is
complete.

### 3.2.1 Definition

Constructor: Optional argument `delay_ms` default 0. Sets a delay between
attempts to acquire the lock. In applications with coros needing frequent
scheduling a nonzero value will facilitate this at the expense of latency.  
Methods:

 * `locked` No args. Returns `True` if locked.
 * `release` No args. Releases the lock.
 * `acquire` No args. Coro which pauses until the lock has been acquired. Use
 by executing `await lock.acquire()`.

## 3.3 Event

This provides a way for one or more coros to pause until another one flags them
to continue. An `Event` object is instantiated and passed to all coros using
it. Coros waiting on the event issue `await event`. Execution pauses
until a coro issues `event.set()`. `event.clear()` must then be issued. An
optional data argument may be passed to `event.set()` and retrieved by
`event.value()`.

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

If multiple coros are to wait on a single event, consider using a `Barrier`
object described below. This is because the coro which raised the event has no
way to determine whether all others have received it; determining when to clear
it down requires further synchronisation. One way to achieve this is with an
acknowledge event:

```python
async def eventwait(event, ack_event):
    await event
    ack_event.set()
```

Example of this are in `event_test` and `ack_test` in asyntest.py.

### 3.3.1 Definition

Constructor: takes one optional boolean argument, defaulting False.
 * `lp` If `True` and the experimental low priority core.py is installed,
 low priority scheduling will be used while awaiting the event. If the standard
 version of uasyncio is installed the arg will have no effect.

Synchronous Methods:
 * `set` Initiates the event. Optional arg `data`: may be of any type,
 sets the event's value. Default `None`.
 * `clear` No args. Clears the event, sets the value to `None`.
 * `is_set` No args. Returns `True` if the event is set.
 * `value` No args. Returns the value passed to `set`.

The optional data value may be used to compensate for the latency in awaiting
the event by passing `loop.time()`.

## 3.4 Barrier

This enables multiple coros to rendezvous at a particular point. For example
producer and consumer coros can synchronise at a point where the producer has
data available and the consumer is ready to use it. At that point in time the
`Barrier` can optionally run a callback before releasing the barrier and
allowing all waiting coros to continue.

Constructor.  
Mandatory arg:  
`participants` The number of coros which will wait on the barrier.  
Optional args:  
`func` Callback to run. Default `None`.  
`args` Tuple of args for the callback. Default `()`.

The callback can be a function or a coro. In most applications a function is
likely to be used: this can be guaranteed to run to completion beore the
barrier is released.

The `Barrier` has no properties or methods for user access. Participant
coros issue `await my_barrier` whereupon execution pauses until all other
participants are also waiting on it. At this point any callback will run and
then each participant will re-commence execution. See `barrier_test` and
`semaphore_test` in asyntest.py for example usage.

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

Constructor: Optional arg `value` default 1. Number of permitted concurrent
accesses.

Synchronous method:
 * `release` No args. Increments the access counter.

Asynchronous method:
 * `acquire` No args. If the access counter is greater than 0, decrements it
 and terminates. Otherwise waits for it to become greater than 0 before
 decrementing it and terminating.

The easiest way to use it is with a context manager:

```python
async def foo(sema):
    async with sema:
        # Limited access here
```

There is a difference between a `Semaphore` and a `Lock`. A `Lock`
instance is owned by the coro which locked it: only that coro can release it. A
`Semaphore` can be released by any coro which acquired it.

### 3.5.1 BoundedSemaphore

This works identically to the `Semaphore` class except that if the `release`
method causes the access counter to exceed its initial value, a `ValueError`
is raised.

## 3.6 Task Cancellation

In `uasyncio` task cancellation is achieved by throwing an exception to the
coro to be cancelled. Cancellation occurs when it is next scheduled. If a coro
issues `await uasyncio.sleep(secs)` or `uasyncio.sleep_ms(ms)` scheduling will
not occur until the time has elapsed. This introduces latency into cancellation
which matters in certain use-cases.

Cancellation is supported by two classes, `NamedTask` and `Cancellable`. The
`NamedTask` class enables a task to be associated with a user supplied name,
enabling it to be cancelled and its status checked.

The `Cancellable` class allows the creation of named groups of anonymous tasks
which may be cancelled as a group. Crucially this awaits confirmation of
completion of cancellation of all tasks in the group.

It is also possible to determine completion of cancellation of `NamedTask`
objects by means of the `Barrier` class. This is detailed below.

For cases where cancellation latency is of concern `asyn.py` offers a `sleep`
function which can reduce this.

### 3.6.1 sleep

Pause for a period as per `uasyncio.sleep` but with reduced exception handling
latency.

The asynchronous `sleep` function takes two args:  
 * `t` Time in seconds. May be integer or float.
 * `granularity` Integer >= 0, units ms. Default 100. Defines the maximum
 latency. Small values reduce latency at cost of increased scheduler workload.

This repetaedly issues `uasyncio.sleep_ms(t)` where t <= `granularity`.

### 3.6.2 NamedTask

A `NamedTask` instance is associated with a user-defined name such that the
name may outlive the task: a coro may end but the class enables its state to be
checked. It may be cancelled with no need to verify that it is still running.
These usage examples assume a user coro `foo` taking two integer arguments.

Instantiation with name 'my foo' can take either of these forms:

```python
await NamedTask('my foo', foo, 1, 2)  # Pause until complete or killed
loop = asyncio.get_event_loop()  # Or schedule and continue:
loop.create_task(NamedTask('my foo', foo, 1, 2)())  # Note () syntax.
```

Cancellation is performed with

```python
NamedTask.cancel('my foo')
```

NamedTask tasks should have the following general form:

```python
async def foo(name, arg1, arg2):  # Receives its name as 1st arg. User args optional.
    try:
        await asyncio.sleep(1)  # Main body of code
        print('Task foo has ended.', arg1, arg2)
    except StopTask:  # Optional cleanup code here
        print('Task foo was cancelled')
    finally:  # Tell the NamedTask class that task has ended
        await NamedTask.end(name)  # Finishes "immediately"
```

The `NamedTask` class is an awaitable class.

Constructor.  
Mandatory args:  
 * `name` Names may be any valid dictionary index. A `ValueError` will be
 raised if the name already exists. If multiple instances of a coro are to run
 concurrently, each should be assigned a different name.
 * `task` A coro passed by name i.e. not using function call syntax.
Optional positional args:  
 * Any further positional args are passed to the coro.  
Optional keyword only arg:  
 * `barrier` A `Barrier` instance may be passed if the cancelling task needs to
 wait for confirmation of successful cancllation.

Class methods:  
 * `cancel` Synchronous. Arg: a coro name.
 The named coro will receive a `CancelError` exception the next time it is
 scheduled. The coro should trap this and quit ASAP. `cancel` will return
 `True` if the coro was cancelled. It will return `False` if the coro has
 already ended or been cancelled.
 * `is_running` Synchronous. Arg: A coro name. Returns `True` if coro is queued
 for scheduling, `False` if has ended or been scheduled for cancellation. See
 note below.
 * `end` Asynchronous. Arg: A coro name. Run by the `NamedTask` instance to
 inform the class that the instance has ended. Completes quickly.
 * `pend_throw` Synchronous. Args: 1. A coro name 2. An exception passed by
 exception class name (not an instance). The named coro will receive an
 instance of the exception the next time it is scheduled.

Bound method:
 * `__call__` This returns the coro and is used to schedule the task using the
 event loop `create_task()` method.

**Latency and Barrier objects**  
Consider the latency discussed at the start of section 3.6. A `NamedTask` has
no mechanism to determine if a cancelled task has been scheduled and has acted
on the `StopTask` exception. Consequently calling `is_running()` on a recently
cancelled task may return `False` even though `uasyncio` will run the task for
one final time.

If a `Barrier` instance is passed to the `NamedTask` constructor, a task
performing cancellation can pause until a set of cancelled tasks have
terminated. The `Barrier` is constructed with the number of dependent tasks
plus one (the task which is to wait on it). It is passed to the constructor of
each dependent task and the cancelling task waits on it after cancelling all
dependent tasks. See examples in `asyntest.py`.

## 3.6.3 Cancellable

The class is aimed at a specific use case where a "teardown" task is required
to cancel a group of other tasks, pausing until all have actually terminated.
`Cancellable` instances are anonymous coros which are members of a named group.
They are capable of being cancelled as a group. Similar functionality can be
achieved with `NamedTask` instances and a `Barrier` but this class provides a
simpler solution. A typical use-case might take this form:

```python
async def comms():  # Perform some communications task
    while True:
        await initialise_link()
        try:
            await do_communications()  # Launches Cancellable tasks
        except CommsError:
            await Cancellable.cancel_all()
        # All sub-tasks are now known to be stopped. They can be re-started
        # with known state on next pass.
```

`Cancellable` tasks are declared with the `cancellable` decorator. They receive
an initial arg which is the class-assigned task number followed by any
user-defined args:

```python
@cancellable
async def print_nums(task_no, num):
    while True:
        print(num)
        num += 1
        await sleep(1)  # asyn.sleep() allows fast response to exception
```

`Cancellable` tasks may be awaited or placed on the event loop:

```python
await Cancellable(print_nums, 5)  # single arg to print_nums.
loop = asyncio.get_event_loop()
loop.create_task(Cancellable(print_nums, 42)())  # Note () syntax.
```

Constructor mandatory args:  
 * `task` A coro passed by name i.e. not using function call syntax.
Constructor optional positional args:  
 * Any further positional args are passed to the coro.
Constructor optional keyword arg:
 * `group` Integer or string. Default 0. See note below.

Class methods:  
 * `cancel_all` Asynchronous. Optional arg `group` default 0. Cancel all
 instances in the specified group and await completion. See note below.
 The named coro will receive a `CancelError` exception the next time it is
 scheduled. The coro should trap this and quit ASAP. The `cancel_all` method
 will terminate when all `Cancellable` instances have handled the `StopTask`
 exception (or terminated naturally before `cancel_all` was launched).
 * `end` Synchronous. Arg: The coro task number. Informs the class that a
 `Cancellable` instance has ended, either normally or by cancellation.
 * `stopped` Asynchronous. Arg: The coro task number. Informs the class that a
 Cancellable instance has been cancelled.

Bound method:
 * `__call__` This returns the coro and is used to schedule the task using the
 event loop `create_task()` method.

**groups**

`Cancellable` tasks may be assigned to groups, identified by a user supplied
integer or string. By default tasks are assigned to group 0. The `cancel_all`
class method cancels all tasks in the specified group. The 0 default ensures
that this facility can be ignored if not required, with `cancel_all` cancelling
all `Cancellable` tasks.

**Custom cleanup**

A task created with the `cancellable` decorator can intercept the `StopTask`
exception to perform custom cleanup operations. This may be done as below:

```python
@cancellable
async def foo(task_no, arg):
    try:
        await sleep(1)  # Main body of task
    except StopTask:
        # perform custom cleanup
        raise  # Propagate exception
```

## 3.8 ExitGate (obsolete)

This was a nasty hack to fake task cancellation at a time when uasyncio did not
support it. The code remains in the module to avoid breaking existing
applications but it will be removed.

# 4 asyntest.py

This provides various test/demo programs. Issue `import asyntest` to see a list
of available tests.
