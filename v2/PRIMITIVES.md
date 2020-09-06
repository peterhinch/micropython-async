# 1. The asyn.py library

This provides some simple synchronisation primitives, together with an API for
task monitoring and cancellation. Task cancellation requires usayncio V 1.7.1
or higher. At the time of writing (7th Jan 2018) it requires a daily build of
MicroPython firmware or one built from source.

The library is too large to run on the ESP8266 except as frozen bytecode. An
obvious workround is to produce a version with unused primitives removed.

###### [Main README](./README.md)

# Contents

 1. [The asyn.py library](./PRIMITIVES.md#1-the-asyn.py-library)  
  1.1 [Synchronisation Primitives](./PRIMITIVES.md#11-synchronisation-primitives)  
  1.2 [Task control and monitoring](./PRIMITIVES.md#12-task-control-and-monitoring)  
 2. [Modules](./PRIMITIVES.md#2-modules)  
 3. [Synchronisation Primitives](./PRIMITIVES.md#3-synchronisation-primitives)  
  3.1 [Function launch](./PRIMITIVES.md#31-function-launch) Launch a function or a coro interchangeably.  
  3.2 [Class Lock](./PRIMITIVES.md#32-class-lock) Ensure exclusive access to a shared resource.  
   3.2.1 [Definition](./PRIMITIVES.md#321-definition)  
  3.3 [Class Event](./PRIMITIVES.md#33-class-event) Pause a coro until an event occurs.  
   3.3.1 [Definition](./PRIMITIVES.md#331-definition)  
  3.4 [Class Barrier](./PRIMITIVES.md#34-class-barrier) Pause multiple coros until all reach a given point.  
  3.5 [Class Semaphore](./PRIMITIVES.md#35-class-semaphore) Limit number of coros which can access a resource.  
   3.5.1 [Class BoundedSemaphore](./PRIMITIVES.md#351-class-boundedsemaphore)  
  3.6 [Class Condition](./PRIMITIVES.md#36-class-condition) Control access to a shared reource.  
   3.6.1 [Definition](./PRIMITIVES.md#361-definition)  
  3.7 [Class Gather](./PRIMITIVES.md#37-class-gather) Synchronise and collect results from multiple coros.  
   3.7.1 [Definition](./PRIMITIVES.md#371-definition)  
   3.7.2 [Use with timeouts and cancellation](./PRIMITIVES.md#372-use-with-timeouts-and-cancellation) Demo of advanced usage of Gather.  
 4. [Task Cancellation](./PRIMITIVES.md#4-task-cancellation) Methods of cancelling tasks and groups of tasks.  
  4.1 [Coro sleep](./PRIMITIVES.md#41-coro-sleep) sleep() with reduced exception handling latency.  
  4.2 [Class Cancellable](./PRIMITIVES.md#42-class-cancellable) Register tasks for cancellation.  
   4.2.1 [Groups](./PRIMITIVES.md#421-groups) Group sets of tasks for cancellation.  
   4.2.2 [Custom cleanup](./PRIMITIVES.md#422-custom-cleanup)  
  4.3 [Class NamedTask](./PRIMITIVES.md#43-class-namedtask) Associate tasks with names for cancellation.  
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
offers "micro" implementations of `Lock`, `Event`, `Barrier`, `Semaphore` and
`Condition` primitives, and a lightweight implementation of `asyncio.gather`.

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
 * `cantest.py` Task cancellation tests. Examples of intercepting `StopTask`.
 Intended to verify the library against future `uasyncio` changes.

Import `asyn_demos.py` or `cantest.py` for a list of available tests.

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

Note that MicroPython had a bug in its implementation of asynchronous context
managers. This is fixed: if you build from source there is no problem. Alas the
fix was too late for release build V1.9.4. If using that build  a `return`
statement should not be issued in the `async with` block. See note at end of
[this section](./TUTORIAL.md#43-asynchronous-context-managers).

### 3.2.1 Definition

Constructor: Optional argument `delay_ms` default 0. Sets a delay between
attempts to acquire the lock. In applications with coros needing frequent
scheduling a nonzero value will reduce the `Lock` object's CPU overhead at the
expense of latency.  
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

Constructor: takes one optional integer argument.
 * `delay_ms` default 0. While awaiting an event an internal flag is repeatedly
 polled. Setting a finite polling interval reduces the task's CPU overhead at
 the expense of increased latency.

Synchronous Methods:
 * `set` Initiates the event. Optional arg `data`: may be of any type,
 sets the event's value. Default `None`. May be called in an interrupt context.
 * `clear` No args. Clears the event, sets the value to `None`.
 * `is_set` No args. Returns `True` if the event is set.
 * `value` No args. Returns the value passed to `set`.

Asynchronous Method:
 * `wait` For CPython compatibility. Pause until event is set. The CPython
 Event is not awaitable.

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
`participants` The number of coros which will use the barrier.  
Optional args:  
`func` Callback to run. Default `None`.  
`args` Tuple of args for the callback. Default `()`.

Public synchronous methods:  
 * `busy` No args. Returns `True` if at least one coro is waiting on the
 barrier, or if at least one non-waiting coro has not triggered it.
 * `trigger` No args. The barrier records that the coro has passed the critical
 point. Returns "immediately".

The callback can be a function or a coro. In most applications a function will
be used as this can be guaranteed to run to completion beore the barrier is
released.

Participant coros issue `await my_barrier` whereupon execution pauses until all
other participants are also waiting on it. At this point any callback will run
and then each participant will re-commence execution. See `barrier_test` and
`semaphore_test` in `asyntest.py` for example usage.

A special case of `Barrier` usage is where some coros are allowed to pass the
barrier, registering the fact that they have done so. At least one coro must
wait on the barrier. That coro will pause until all non-waiting coros have
passed the barrier, and all waiting coros have reached it. At that point all
waiting coros will resume. A non-waiting coro issues `barrier.trigger()` to
indicate that is has passed the critical point.

This mechanism is used in the `Cancellable` and `NamedTask` classes to register
the fact that a coro has responded to cancellation. Using a non-waiting barrier
in a looping construct carries a fairly obvious hazard and is normally to be
avoided.

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

## 3.6 Class Condition

A `Condition` instance enables controlled access to a shared resource. In
typical applications a number of tasks wait for the resource to be available.
Once this occurs access can be controlled both by the number of tasks and by
means of a `Lock`.

A task waiting on a `Condition` instance will pause until another task issues
`condition.notify(n)` or `condition.notify_all()`. If the number of tasks
waiting on the condition exceeds `n`, only `n` tasks will resume. A `Condition`
instance has a `Lock` as a member. A task will only resume when it has acquired
the lock. User code may release the lock as required by the application logic.

Typical use of the class is in a synchronous context manager:

```python
    with await cond:
        cond.notify(2)  # Notify 2 tasks
```

```python
    with await cond:
        await cond.wait()
        # Has been notified and has access to the locked resource
    # Resource has been unocked by context manager
```
### 3.6.1 Definition

Constructor: Optional arg `lock=None`. A `Lock` instance may be specified,
otherwise the `Condition` instantiates its own.

Synchronous methods:  
 * `locked` No args. Returns the state of the `Lock` instance.
 * `release` No args. Release the `Lock`. A `RuntimeError` will occur if the
 `Lock` is not locked.
 * `notify` Arg `n=1`. Notify `n` tasks. The `Lock` must be acquired before
 issuing `notify` otherwise a `RuntimeError` will occur.
 * `notify_all` No args. Notify all tasks. The `Lock` must be acquired before
 issuing `notify_all` otherwise a `RuntimeError` will occur.

Asynchronous methods:  
 * `acquire` No args. Pause until the `Lock` is acquired.
 * `wait` No args. Await notification and the `Lock`. The `Lock` must be
 acquired before issuing `wait` otherwise a `RuntimeError` will occur. The
 sequence is as follows:  
 The `Lock` is released.  
 The task pauses until another task issues `notify`.  
 It continues to pause until the `Lock` has been re-acquired when execution
 resumes.
 * `wait_for` Arg: `predicate` a callback returning a `bool`. The task pauses
 until a notification is received and an immediate test of `predicate()`
 returns `True`.

###### [Contents](./PRIMITIVES.md#contents)

## 3.7 Class Gather

This aims to replicate some of the functionality of `asyncio.gather` in a
'micro' form. The user creates a list of `Gatherable` tasks and then awaits a
`Gather` object. When the last task to complete terminates, this will return a
list of results returned by the tasks. Timeouts may be assigned to individual
tasks.

```python
async def foo(n):
    await asyncio.sleep(n)
    return n * n

async def bar(x, y, rats):  # Example coro: note arg passing
    await asyncio.sleep(1)
    return x * y * rats

gatherables = [asyn.Gatherable(foo, n) for n in range(4)]
gatherables.append(asyn.Gatherable(bar, 7, 8, rats=77))
gatherables.append(asyn.Gatherable(rats, 0, timeout=5))
res = await asyn.Gather(gatherables)
```

The result `res` is a 6 element list containing the result of each of the 6
coros. These are ordered by the position of the coro in the `gatherables` list.
This is as per `asyncio.gather()`.

See `asyntest.py` function `gather_test()`.

### 3.7.1 Definition

The `Gatherable` class has no user methods. The constructor takes a coro by
name followed by any positional or keyword arguments for the coro. If an arg
`timeout` is provided it should have an integer or float value: this is taken
to be the timeout for the coro in seconds. Note that timeout is subject to the
latency discussed in [Coroutines with timeouts](./TUTORIAL.md#44-coroutines-with-timeouts).
A way to reduce this is to use `asyn.sleep()` in such coros.

The `Gather` class has no user methods. The constructor takes one mandatory
arg: a list of `Gatherable` instances.

`Gather` instances are awaitable. An `await` on an instance will terminate when
the last member task completes or times out. It returns a list whose length
matches the length of the list of `Gatherable` instances. Each element contains
the return value of the corresponding `Gatherable` instance. Each return value
may be of any type.

### 3.7.2 Use with timeouts and cancellation

The following complete example illustrates the use of `Gather` with tasks which
are subject to cancellation or timeout.

```python
import uasyncio as asyncio
import asyn

async def barking(n):
    print('Start normal coro barking()')
    for _ in range(6):
        await asyncio.sleep(1)
    print('Done barking.')
    return 2 * n

async def foo(n):
    print('Start timeout coro foo()')
    try:
        while True:
            await asyncio.sleep(1)
            n += 1
    except asyncio.TimeoutError:
        print('foo timeout.')
    return n

@asyn.cancellable
async def bar(n):
    print('Start cancellable bar()')
    try:
        while True:
            await asyncio.sleep(1)
            n += 1
    except asyn.StopTask:
        print('bar stopped.')
    return n

async def do_cancel():
    await asyncio.sleep(5.5)
    await asyn.Cancellable.cancel_all()

async def main(loop):
    bar_task = asyn.Cancellable(bar, 70)  # Note args here
    gatherables = [asyn.Gatherable(barking, 21),
                   asyn.Gatherable(foo, 10, timeout=7.5),
                   asyn.Gatherable(bar_task)]
    loop.create_task(do_cancel())
    res = await asyn.Gather(gatherables)
    print('Result: ', res)  # Expect  [42, 17, 75]

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))
```

###### [Contents](./PRIMITIVES.md#contents)

# 4. Task Cancellation

All current `uasyncio` versions have a `cancel(coro)` function. This works by
throwing an exception to the coro in a special way: cancellation is deferred
until the coro is next scheduled. This mechanism works with nested coros.

There is a limitation with official `uasyncio` V2.0. In this version a coro
which is waiting on a `sleep()` or `sleep_ms()` or pending I/O will not get the
exception until it is next scheduled. This means that cancellation can take a
long time: there is often a need to be able to verify when this has occurred.

This problem can now be circumvented in two ways both involving running
unofficial code. The solutions fix the problem by ensuring that the cancelled
coro is scheduled promptly. Assuming `my_coro` is coded normally the following
will ensure that cancellation is complete, even if `my_coro` is paused at the
time of cancellation:
```python
my_coro_instance = my_coro()
loop.add_task(my_coro_instance)
# Do something
asyncio.cancel(my_coro_instance)
await asyncio.sleep(0)
# The task is now cancelled
```
The unofficial solutions are:
 * To run the `fast_io` version of `uasyncio` presented her, with official
 MicroPython firmware.
 * To run [Paul Sokolovsky's Pycopy firmware fork](https://github.com/pfalcon/pycopy)
 plus `uasyncio` V2.4 from
 [Paul Sokolovsky's library fork](https://github.com/pfalcon/micropython-lib)

The following describes workrounds for those wishing to run official code (for
example the current realease build which includes `uasyncio` V2.0). There is
usually a need to establish when cancellation has occured: the classes and 
decorators described below facilitate this.

If a coro issues `await uasyncio.sleep(secs)` or `await uasyncio.sleep_ms(ms)`
scheduling will not occur until the time has elapsed. This introduces latency
into cancellation which matters in some use-cases. Other potential sources of
latency take the form of slow code. `uasyncio` V2.0 has no mechanism for
verifying when cancellation has actually occurred. The `asyn.py` library
provides solutions in the form of two classes.

These are `Cancellable` and `NamedTask`. The `Cancellable` class allows the
creation of named groups of tasks which may be cancelled as a group; this
awaits completion of cancellation of all tasks in the group.

The `NamedTask` class enables a task to be associated with a user supplied
name, enabling it to be cancelled and its status checked. Cancellation
optionally awaits confirmation of completion.

For cases where cancellation latency is of concern `asyn.py` offers a `sleep`
function which provides a delay with reduced latency.

## 4.1 Coro sleep

Pause for a period as per `uasyncio.sleep` but with reduced exception handling
latency.

The asynchronous `sleep` function takes two args:  
 * `t` Mandatory. Time in seconds. May be integer or float.
 * `granularity` Optional integer >= 0, units ms. Default 100ms. Defines the
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
            await asyn.Cancellable.cancel_all()
        # All sub-tasks are now known to be stopped. They can be re-started
        # with known initial state on next pass.
```

A `Cancellable` task is declared with the `@cancellable` decorator:

```python
@asyn.cancellable
async def print_nums(num):
    while True:
        print(num)
        num += 1
        await sleep(1)  # asyn.sleep() allows fast response to exception
```

Positional or keyword arguments for the task are passed to the `Cancellable`
constructor as below. Note that the coro is passed not using function call
syntax. `Cancellable` tasks may be awaited or placed on the event loop:

```python
await asyn.Cancellable(print_nums, 5)  # single arg to print_nums.
loop = asyncio.get_event_loop()
loop.create_task(asyn.Cancellable(print_nums, 42)())  # Note () syntax.
```
**NOTE** A coro declared with `@asyn.cancellable` must only be launched using
the above syntax options. Treating it as a conventional coro will result in
`tuple index out of range` errors or other failures.

The following will cancel any tasks still running, pausing until cancellation
is complete:

```python
await asyn.Cancellable.cancel_all()
```

Constructor mandatory args:  
 * `task` A coro passed by name i.e. not using function call syntax.

Constructor optional positional args:  
 * Any further positional args are passed to the coro.

Constructor optional keyword args:  
 * `group` Any Python object, typically integer or string. Default 0. See
 Groups below.
 * Further keyword args are passed to the coro.

Public class method:  
 * `cancel_all` Asynchronous.  
 Optional args `group` default 0, `nowait` default `False`.
 The `nowait` arg is for use by the `NamedTask` derived class. The default
 value is assumed below.  
 The method cancels all instances in the specified group and awaits completion.
 See Groups below.  
 The `cancel_all` method will complete when all `Cancellable` instances have
 been cancelled or terminated naturally before `cancel_all` was launched.  
 Each coro will receive a `StopTask` exception when it is next scheduled. If
 the coro is written using the `@cancellable` decorator this is handled
 automatically.  
 It is possible to trap the `StopTask` exception: see 'Custom cleanup' below.

Public bound method:
 * `__call__` This returns the coro and is used to schedule the task using the
 event loop `create_task()` method using function call syntax.

The `asyn.StopTask` exception is an alias for `usayncio.CancelledError`. In my
view the name is more descriptive of its function.

A complete minimal, example:
```python
import uasyncio as asyncio
import asyn

@asyn.cancellable
async def print_nums(num):
    while True:
        print(num)
        num += 1
        await asyn.sleep(1)  # asyn.sleep() allows fast response to exception

async def main(loop):
    loop.create_task(asyn.Cancellable(print_nums, 42)())  # Note () syntax
    await asyncio.sleep(5)
    await asyn.Cancellable.cancel_all()
    print('Task cancelled: delay 3 secs to prove it.')
    await asyncio.sleep(3)

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))
```

### 4.2.1 Groups

`Cancellable` tasks may be assigned to groups, identified by a user supplied
Python object, typically an integer or string. By default tasks are assigned to
group 0. The `cancel_all` class method cancels all tasks in the specified
group. The 0 default ensures that this facility can be ignored if not required,
with `cancel_all` cancelling all `Cancellable` tasks.

### 4.2.2 Custom cleanup

A task created with the `cancellable` decorator can intercept the `StopTask`
exception to perform custom cleanup operations. This may be done as below:
```python
@asyn.cancellable
async def foo():
    while True:
        try:
            await sleep(1)  # Main body of task
        except asyn.StopTask:
            # perform custom cleanup
            return  # Respond by quitting
```
The following example returns `True` if it ends normally or `False` if
cancelled.
```python
@asyn.cancellable
async def bar():
    try:
        await sleep(1)  # Main body of task
    except asyn.StopTask:
        return False
    else:
        return True
```
A complete minimal example:
```python
import uasyncio as asyncio
import asyn

@asyn.cancellable
async def print_nums(num):
    try:
        while True:
            print(num)
            num += 1
            await asyn.sleep(1)  # asyn.sleep() allows fast response to exception
    except asyn.StopTask:
        print('print_nums was cancelled')

async def main(loop):
    loop.create_task(asyn.Cancellable(print_nums, 42)())  # Note () syntax
    await asyncio.sleep(5)
    await asyn.Cancellable.cancel_all()
    print('Task cancelled: delay 3 secs to prove it.')
    await asyncio.sleep(3)

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))
```

###### [Contents](./PRIMITIVES.md#contents)

## 4.3 Class NamedTask

A `NamedTask` instance is associated with a user-defined name such that the
name may outlive the task: a coro may end but the class enables its state to be
checked. It is a subclass of `Cancellable` and its constructor disallows
duplicate names: each instance of a coro must be assigned a unique name.

A `NamedTask` coro is defined with the `@cancellable` decorator.

```python
@cancellable
async def foo(arg1, arg2):
    await asyn.sleep(1)
    print('Task foo has ended.', arg1, arg2)
```

The `NamedTask` constructor takes the name, the coro, plus any user positional
or keyword args. The resultant instance can be scheduled in the usual ways:

```python
await asyn.NamedTask('my foo', foo, 1, 2)  # Pause until complete or killed
loop = asyncio.get_event_loop()  # Or schedule and continue:
loop.create_task(asyn.NamedTask('my nums', foo, 10, 11)())  # Note () syntax.
```

Cancellation is performed with:

```python
await asyn.NamedTask.cancel('my foo')
```

When cancelling a task there is no need to check if the task is still running:
if it has already completed, cancellation will have no effect.

NamedTask Constructor.  
Mandatory args:  
 * `name` Names may be any immutable type capable of being a dictionary index
 e.g. integer or string. A `ValueError` will be raised if the name is already
 assigned by a running coro. If multiple instances of a coro are to run
 concurrently, each should be assigned a different name.
 * `task` A coro passed by name i.e. not using function call syntax.

 Optional positional args:  
 * Any further positional args are passed to the coro.  

 Optional keyword only args:  
 * `barrier` A `Barrier` instance may be passed. See below.
 * Further keyword args are passed to the coro.

Public class methods:  
 * `cancel` Asynchronous.  
 Mandatory arg: a coro name.  
 Optional boolean arg `nowait` default `True`  
 By default it will return soon. If `nowait` is `False` it will pause until the
 coro has completed cancellation.  
 The named coro will receive a `StopTask` exception the next time it is
 scheduled. If the `@namedtask` decorator is used this is transparent to the
 user but the exception may be trapped for custom cleanup (see below).  
 `cancel` will return `True` if the coro was cancelled. It will return `False`
 if the coro has already ended or been cancelled.  
 * `is_running` Synchronous. Arg: A coro name. Returns `True` if coro is queued
 for scheduling, `False` if it has ended or been cancelled.

Public bound method:
 * `__call__` This returns the coro and is used to schedule the task using the
 event loop `create_task()` method using function call syntax.

### 4.3.1 Latency and Barrier objects

It is possible to get confirmation of cancellation of an arbitrary set of
`NamedTask` instances by instantiating a `Barrier` and passing it to the
constructor of each member. This enables more complex synchronisation cases
than the normal method of using a group of `Cancellable` tasks. The approach is
described below.

If a `Barrier` instance is passed to the `NamedTask` constructor, a task
performing cancellation can pause until a set of cancelled tasks have
terminated. The `Barrier` is constructed with the number of dependent tasks
plus one (the task which is to wait on it). It is passed to the constructor of
each dependent task and the cancelling task waits on it after cancelling all
dependent tasks. Each task being cancelled terminates 'immediately' subject
to latency.

See examples in `cantest.py` e.g. `cancel_test2()`.

### 4.3.2 Custom cleanup

A coroutine to be used as a `NamedTask` can intercept the `StopTask` exception
if necessary. This might be done for cleanup or to return a 'cancelled' status.
The coro should have the following form:

```python
@asyn.cancellable
async def foo():
    try:
        await asyncio.sleep(1)  # User code here
    except asyn.StopTask:
        return False  # Cleanup code
    else:
        return True  # Normal exit
```

###### [Contents](./PRIMITIVES.md#contents)
