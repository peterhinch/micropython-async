# 1. The asyn.py library

This provides five simple synchronisation primitives, together with an API for
task monitoring and cancellation. Task cancellation requires usayncio V 1.7.1
or higher. At the time of writing (7th Jan 2018) it requires a daily build of
MicroPython firmware or one built from source.

###### [Main README](./README.md)

# Contents

 1. [The asyn.py library](./PRIMITIVES.md#1-the-asyn.py-library)

  1.1 [Synchronisation Primitives](./PRIMITIVES.md#11-synchronisation-primitives)

  1.2 [Task control and monitoring](./PRIMITIVES.md#12-task-control-and-monitoring)

 2. [Modules](./PRIMITIVES.md#2-modules)
 
 3 [Synchronisation Primitives](./PRIMITIVES.md#3-synchronisation-primitives)

  3.1 [Function launch](./PRIMITIVES.md#31-function-launch)

  3.2 [Class Lock](./PRIMITIVES.md#32-class-lock)

   3.2.1 [Definition](./PRIMITIVES.md#321-definition)

  3.3 [Class Event](./PRIMITIVES.md#33-class-event)

   3.3.1 [Definition](./PRIMITIVES.md#331-definition)

  3.4 [Class Barrier](./PRIMITIVES.md#34-class-barrier)

  3.5 [Class Semaphore](./PRIMITIVES.md#35-class-semaphore)

   3.5.1 [Class BoundedSemaphore](./PRIMITIVES.md#351-class-boundedsemaphore)
  
 4. [Task Cancellation](./PRIMITIVES.md#4-task-cancellation)

  4.1 [Coro sleep](./PRIMITIVES.md#41-coro-sleep)

  4.2 [Class Cancellable](./PRIMITIVES.md#42-class-cancellable)

   4.2.1 [Groups](./PRIMITIVES.md#421-groups)

   4.2.2 [Custom cleanup](./PRIMITIVES.md#422-custom-cleanup)

  4.3 [Class NamedTask](./PRIMITIVES.md#43-class-namedtask)

   4.3.1 [Latency and Barrier objects](./PRIMITIVES.md#431-latency-and-barrier-objects)

   4.3.2 [Custom cleanup](./PRIMITIVES.md#432-custom-cleanup)

## 1.1 Synchronisation Primitives

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

###### [Contents](./PRIMITIVES.md#contents)

## 1.2 Task control and monitoring

`uasyncio` does not implement the `Task` and `Future` classes of `asyncio`.
Instead it uses a 'micro' lightweight means of task cancellation. The `asyn.py`
module provides an API to simplify its use and to check on the running status
of coroutines which are subject to cancellation.

# 2. Modules

The following modules are provided:
 * `asyn.py` The main library.
 * `asyntest.py` Test/demo programs for the primitives.
 * `asyn_demos.py` Minimal "get started" task cancellation demos.
 * `cantest.py` Task cancellation tests.

Import the test or demo module for a list of available tests.

###### [Contents](./PRIMITIVES.md#contents)

# 3. Synchronisation Primitives

The primitives are intended for use only with `uasyncio`. They are `micro` in
design. They are not thread safe and hence are incompatible with the `_thread`
module and with interrupt handlers.

## 3.1 Function launch

This function accepts a function or coro as an argument, along with a tuple of
args. If the function is a callback it is executed with the supplied argumets.
If it is a coro, it is scheduled for execution.

args:
 * `func` Mandatory. a function or coro. These are provided 'as-is' i.e. not
 using function call syntax.
 * `tup_args` Optional. A tuple of arguments, default `()`. The args are
 upacked when provided to the function.

## 3.2 Class Lock

This has now been superseded by the more efficient official version.

At time of writing (18th Dec 2017) the official `Lock` class is not complete.
If a coro is subject to a [timeout](./TUTORIAL.md#44-coroutines-with-timeouts)
and the timeout is triggered while it is waiting on a lock, the timeout will be
ineffective. It will not receive the `TimeoutError` until it has acquired the
lock.

The implementation in `asyn.py` avoids this limitation but at the cost of lower
efficiency. The remainder of this section describes this version.

A lock guarantees unique access to a shared resource. The preferred way to use it
is via an asynchronous context manager. In the following code sample a `Lock`
instance `lock` has been created and is passed to all coros wishing to access
the shared resource. Each coro issues the following:

```python
async def bar(lock):
    async with lock:
        # Access resource
```

While the coro `bar` is accessing the resource, other coros will pause at the
`async with lock` statement until the context manager in `bar()` is complete.

Note that MicroPython has a bug in its implementation of asynchronous context
managers: a `return` statement should not be issued in the `async with` block.
See note at end of [this section](./TUTORIAL.md#43-asynchronous-context-managers).

### 3.2.1 Definition

Constructor: Optional argument `delay_ms` default 0. Sets a delay between
attempts to acquire the lock. In applications with coros needing frequent
scheduling a nonzero value will facilitate this at the expense of latency.  
Methods:

 * `locked` No args. Returns `True` if locked.
 * `release` No args. Releases the lock.
 * `acquire` No args. Coro which pauses until the lock has been acquired. Use
 by executing `await lock.acquire()`.

###### [Contents](./PRIMITIVES.md#contents)

## 3.3 Class Event

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

###### [Contents](./PRIMITIVES.md#contents)

## 3.4 Class Barrier

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

###### [Contents](./PRIMITIVES.md#contents)

## 3.5 Class Semaphore

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

### 3.5.1 Class BoundedSemaphore

This works identically to the `Semaphore` class except that if the `release`
method causes the access counter to exceed its initial value, a `ValueError`
is raised.

###### [Contents](./PRIMITIVES.md#contents)

# 4. Task Cancellation

Note to users of releases prior to 31st Dec 2017: this API has changed. It
should now be stable.

In `uasyncio` task cancellation is achieved by throwing an exception to the
coro to be cancelled in a special way: cancellation is deferred until the coro
is next scheduled. This mechanism works with nested coros. However there is a
limitation. If a coro issues `await uasyncio.sleep(secs)` or
`uasyncio.sleep_ms(ms)` scheduling will not occur until the time has elapsed.
This introduces latency into cancellation which matters in some use-cases.

Cancellation is supported by two classes, `Cancellable` and `NamedTask`. The
`Cancellable` class allows the creation of named groups of anonymous tasks
which may be cancelled as a group. Crucially this awaits actual completion of
cancellation of all tasks in the group.

The `NamedTask` class enables a task to be associated with a user supplied
name, enabling it to be cancelled and its status checked. Cancellation does not
await confirmation of completion. This may be achieved by means of a `Barrier`
instance although the normal approach is to use a `Cancellable` task.

For cases where cancellation latency is of concern `asyn.py` offers a `sleep`
function which can reduce this.

## 4.1 Coro sleep

Pause for a period as per `uasyncio.sleep` but with reduced exception handling
latency.

The asynchronous `sleep` function takes two args:  
 * `t` Mandatory. Time in seconds. May be integer or float.
 * `granularity` Optional. Integer >= 0, units ms. Default 100ms. Defines the
 maximum latency. Small values reduce latency at cost of increased scheduler
 workload.

This repeatedly issues `uasyncio.sleep_ms(t)` where t <= `granularity`.

## 4.2 Class Cancellable

This class provides for cancellation of one or more tasks where it is necesary
to await confirmation that cancellation is complete. `Cancellable` instances
are anonymous coros which are members of a named group. They are capable of
being cancelled as a group. A typical use-case might take this form:

```python
async def comms():  # Perform some communications task
    while True:
        await initialise_link()
        try:
            await do_communications()  # Launches Cancellable tasks
        except CommsError:
            await Cancellable.cancel_all()
        # All sub-tasks are now known to be stopped. They can be re-started
        # with known initial state on next pass.
```

A `Cancellable` task is declared with the `@cancellable` decorator. When
scheduled it will receive an initial arg which is a `TaskId` instance followed
by any user-defined args. The `TaskId` instance can be ignored unless custom
cleanup is required (see below).

```python
@cancellable
async def print_nums(task_id, num):
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

The following will cancel any tasks still running, pausing until cancellation
is complete:

```python
await Cancellable.cancel_all()
```

Constructor mandatory args:  
 * `task` A coro passed by name i.e. not using function call syntax.

Constructor optional positional args:  
 * Any further positional args are passed to the coro.

 Constructor optional keyword arg:  
 * `group` Integer or string. Default 0. See Groups below.

Class methods:  
 * `cancel_all` Asynchronous. Optional arg `group` default 0.  
 Cancel all instances in the specified group and await completion. See Groups
 below.  
 The `cancel_all` method will complete when all `Cancellable` instances have
 been cancelled or terminated naturally before `cancel_all` was launched.  
 Each coro will receive a `CancelError` exception when it is next scheduled.
 The coro should trap this, await the `stopped` method and quit. If the coro
 quits for any reason it should call the `end` method. The `@cancellable`
 decorator handles the above housekeeping.
 * `end` Synchronous. Arg: The coro task number. Informs the class that a
 `Cancellable` instance has ended, either normally or by cancellation.
 * `stopped` Asynchronous. Arg: The coro task number. Informs the class that a
 Cancellable instance has been cancelled.

Bound method:
 * `__call__` This returns the coro and is used to schedule the task using the
 event loop `create_task()` method.

### 4.2.1 Groups

`Cancellable` tasks may be assigned to groups, identified by a user supplied
integer or string. By default tasks are assigned to group 0. The `cancel_all`
class method cancels all tasks in the specified group. The 0 default ensures
that this facility can be ignored if not required, with `cancel_all` cancelling
all `Cancellable` tasks.

### 4.2.2 Custom cleanup

A task created with the `cancellable` decorator can intercept the `StopTask`
exception to perform custom cleanup operations. This may be done as below:

```python
@cancellable
async def foo(task_id, arg):
    try:
        await sleep(1)  # Main body of task
    except StopTask:
        # perform custom cleanup
        raise  # Propagate exception to closure
```

Where full control is required a cancellable task should be written without the
decorator. The following example returns `True` if it ends normally or `False`
if cancelled.

```python
async def bar(task_id):
    task_no = task_id()  # Retrieve task no. from TaskId instance
    try:
        await sleep(1)
    except StopTask:
        await Cancellable.stopped(task_no)
        return False
    else:
        return True
    finally:
        Cancellable.end(task_no)
```

###### [Contents](./PRIMITIVES.md#contents)

## 4.3 Class NamedTask

A `NamedTask` instance is associated with a user-defined name such that the
name may outlive the task: a coro may end but the class enables its state to be
checked.

A `NamedTask` task is defined with the `@namedtask` decorator. When scheduled it
will receive an initial arg which is the name followed by any user-defined args.

```python
@namedtask
async def foo(name, arg1, arg2):
    await asyn.sleep(1)
    print('Task foo has ended.', arg1, arg2)
```

The `NamedTask` constructor takes the name, the coro, plus any user args. The
resultant instance can be scheduled in the usual ways:

```python
await NamedTask('my foo', foo, 1, 2)  # Pause until complete or killed
loop = asyncio.get_event_loop()  # Or schedule and continue:
loop.create_task(NamedTask('my nums', foo, 10, 11)())  # Note () syntax.
```

Cancellation is performed with

```python
NamedTask.cancel('my foo')
```

When cancelling a task there is no need to check if the task is still running:
if it has already completed, cancellation will have no effect.

NamedTask Constructor.  
Mandatory args:  
 * `name` Names may be any immutable type e.g. integer or string. A
 `ValueError` will be raised if the name already exists. If multiple instances
 of a coro are to run concurrently, each should be assigned a different name.
 * `task` A coro passed by name i.e. not using function call syntax.

 Optional positional args:  
 * Any further positional args are passed to the coro.  

 Optional keyword only arg:  
 * `barrier` A `Barrier` instance may be passed if the cancelling task needs to
 wait for confirmation of successful cancellation.

Class methods:  
 * `cancel` Synchronous. Arg: a coro name.  
 The named coro will receive a `CancelError` exception the next time it is
 scheduled. The coro should trap this, ensure the `end` bound coro is launched
 and return. The `@namedtask` decorator handles this, ensuring `end` is called
 under all circumstances.  
 `cancel` will return `True` if the coro was cancelled. It will return `False`
 if the coro has already ended or been cancelled.
 * `is_running` Synchronous. Arg: A coro name. Returns `True` if coro is queued
 for scheduling, `False` if it has ended or been scheduled for cancellation.
 See note in 4.3.1 below.
 * `end` Asynchronous. Arg: A coro name. Run by the `NamedTask` instance to
 inform the class that the instance has ended. Completes quickly.

Bound method:
 * `__call__` This returns the coro and is used to schedule the task using the
 event loop `create_task()` method.

### 4.3.1 Latency and Barrier objects

Consider the latency discussed at the start of section 3.6: cancellation raises
an exception which will be handled when the coro is next scheduled. There is no
mechanism to determine if a cancelled task has been scheduled and has acted on
the `StopTask` exception. Consequently calling `is_running()` on a recently
cancelled task may return `False` even though `uasyncio` will run the task for
one final time.

Confirmation of cancellation may be achieved by means of a `Barrier` object,
however practical use-cases for this are few - if confirmation is required the
normal approach is to use `Cancellable` tasks, if necessary in groups having a
single member. However the approach is described below.

If a `Barrier` instance is passed to the `NamedTask` constructor, a task
performing cancellation can pause until a set of cancelled tasks have
terminated. The `Barrier` is constructed with the number of dependent tasks
plus one (the task which is to wait on it). It is passed to the constructor of
each dependent task and the cancelling task waits on it after cancelling all
dependent tasks. Note that the tasks being cancelled terminate immediately.

See examples in `cantest.py` e.g. `cancel_test2()`.

### 4.3.2 Custom cleanup

A task created with the `@namedtask` decorator can intercept the `StopTask`
exception if necessary. This might be done for cleanup or to return a
'cancelled' status.

```python
@namedtask
async def foo(_):
    try:
        await asyncio.sleep(1)  # User code here
        return True
    except StopTask:
        return False
```

###### [Contents](./PRIMITIVES.md#contents)

#### ExitGate (obsolete)

This was a nasty hack to fake task cancellation at a time when uasyncio did not
support it. The code remains in the module to avoid breaking existing
applications but it will be removed.
