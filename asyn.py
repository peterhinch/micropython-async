# asyn.py 'micro' synchronisation primitives for uasyncio
# Test/demo programs asyntest.py, barrier_test.py
# Provides Lock, Event, Barrier, Semaphore, BoundedSemaphore, Condition,
# NamedTask and Cancellable classes, also sleep coro.
# Updated 31 Dec 2017 for uasyncio.core V1.6 and to provide task cancellation.

# The MIT License (MIT)
#
# Copyright (c) 2017 Peter Hinch
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# CPython 3.5 compatibility
# (ignore RuntimeWarning: coroutine '_g' was never awaited)

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


async def _g():
    pass
type_coro = type(_g())

# If a callback is passed, run it and return.
# If a coro is passed initiate it and return.
# coros are passed by name i.e. not using function call syntax.
def launch(func, tup_args):
    res = func(*tup_args)
    if isinstance(res, type_coro):
        loop = asyncio.get_event_loop()
        loop.create_task(res)


# To access a lockable resource a coro should issue
# async with lock_instance:
#    access the locked resource

# Alternatively:
# await lock.acquire()
# try:
#   do stuff with locked resource
# finally:
#   lock.release
# Uses normal scheduling on assumption that locks are held briefly.
class Lock():
    def __init__(self, delay_ms=0):
        self._locked = False
        self.delay_ms = delay_ms

    def locked(self):
        return self._locked

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        self.release()
        await asyncio.sleep(0)

    async def acquire(self):
        while True:
            if self._locked:
                await asyncio.sleep_ms(self.delay_ms)
            else:
                self._locked = True
                break

    def release(self):
        if not self._locked:
            raise RuntimeError('Attempt to release a lock which has not been set')
        self._locked = False


# A coro waiting on an event issues await event
# A coro rasing the event issues event.set()
# When all waiting coros have run
# event.clear() should be issued
class Event():
    def __init__(self, delay_ms=0):
        self.delay_ms = delay_ms
        self.clear()

    def clear(self):
        self._flag = False
        self._data = None

    async def wait(self):  # CPython comptaibility
        while not self._flag:
            await asyncio.sleep_ms(self.delay_ms)

    def __await__(self):
        while not self._flag:
            await asyncio.sleep_ms(self.delay_ms)

    __iter__ = __await__

    def is_set(self):
        return self._flag

    def set(self, data=None):
        self._flag = True
        self._data = data

    def value(self):
        return self._data

# A Barrier synchronises N coros. Each issues await barrier.
# Execution pauses until all other participant coros are waiting on it.
# At that point the callback is executed. Then the barrier is 'opened' and
# execution of all participants resumes.

# The nowait arg is to support task cancellation. It enables usage where one or
# more coros can register that they have reached the barrier without waiting
# for it. Any coros waiting normally on the barrier will pause until all
# non-waiting coros have passed the barrier and all waiting ones have reached
# it. The use of nowait promotes efficiency by enabling tasks which have been
# cancelled to leave the task queue as soon as possible.

class Barrier():
    def __init__(self, participants, func=None, args=()):
        self._participants = participants
        self._func = func
        self._args = args
        self._reset(True)

    def __await__(self):
        self._update()
        if self._at_limit():  # All other threads are also at limit
            if self._func is not None:
                launch(self._func, self._args)
            self._reset(not self._down)  # Toggle direction to release others
            return

        direction = self._down
        while True:  # Wait until last waiting thread changes the direction
            if direction != self._down:
                return
            yield

    __iter__ = __await__

    def trigger(self):
        self._update()
        if self._at_limit():  # All other threads are also at limit
            if self._func is not None:
                launch(self._func, self._args)
            self._reset(not self._down)  # Toggle direction to release others

    def _reset(self, down):
        self._down = down
        self._count = self._participants if down else 0

    def busy(self):
        if self._down:
            done = self._count == self._participants
        else:
            done = self._count == 0
        return not done

    def _at_limit(self):  # Has count reached up or down limit?
        limit = 0 if self._down else self._participants
        return self._count == limit

    def _update(self):
        self._count += -1 if self._down else 1
        if self._count < 0 or self._count > self._participants:
            raise ValueError('Too many tasks accessing Barrier')

# A Semaphore is typically used to limit the number of coros running a
# particular piece of code at once. The number is defined in the constructor.
class Semaphore():
    def __init__(self, value=1):
        self._count = value

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        self.release()
        await asyncio.sleep(0)

    async def acquire(self):
        while self._count == 0:
            yield
        self._count -= 1

    def release(self):
        self._count += 1

class BoundedSemaphore(Semaphore):
    def __init__(self, value=1):
        super().__init__(value)
        self._initial_value = value

    def release(self):
        if self._count < self._initial_value:
            self._count += 1
        else:
            raise ValueError('Semaphore released more than acquired')

# Task Cancellation
try:
    StopTask = asyncio.CancelledError  # More descriptive name
except AttributeError:
    raise OSError('asyn.py requires uasyncio V1.7.1 or above.')

class TaskId():
    def __init__(self, taskid):
        self.taskid = taskid

    def __call__(self):
        return self.taskid

# Sleep coro breaks up a sleep into shorter intervals to ensure a rapid
# response to StopTask exceptions. Only relevant to official uasyncio V2.0.
async def sleep(t, granularity=100):  # 100ms default
    if granularity <= 0:
        raise ValueError('sleep granularity must be > 0')
    t = int(t * 1000)  # ms
    if t <= granularity:
        await asyncio.sleep_ms(t)
    else:
        n, rem = divmod(t, granularity)
        for _ in range(n):
            await asyncio.sleep_ms(granularity)
        await asyncio.sleep_ms(rem)

# Anonymous cancellable tasks. These are members of a group which is identified
# by a user supplied name/number (default 0). Class method cancel_all() cancels
# all tasks in a group and awaits confirmation. Confirmation of ending (whether
# normally or by cancellation) is signalled by a task calling the _stopped()
# class method. Handled by the @cancellable decorator.


class Cancellable():
    task_no = 0  # Generated task ID, index of tasks dict
    tasks = {}  # Value is [coro, group, barrier] indexed by integer task_no

    @classmethod
    def _cancel(cls, task_no):
        task = cls.tasks[task_no][0]
        asyncio.cancel(task)

    @classmethod
    async def cancel_all(cls, group=0, nowait=False):
        tokill = cls._get_task_nos(group)
        barrier = Barrier(len(tokill) + 1)  # Include this task
        for task_no in tokill:
            cls.tasks[task_no][2] = barrier
            cls._cancel(task_no)
        if nowait:
            barrier.trigger()
        else:
            await barrier

    @classmethod
    def _is_running(cls, group=0):
        tasks = cls._get_task_nos(group)
        if tasks == []:
            return False
        for task_no in tasks:
            barrier = cls.tasks[task_no][2]
            if barrier is None:  # Running, not yet cancelled
                return True
            if barrier.busy():
                return True
        return False

    @classmethod
    def _get_task_nos(cls, group):  # Return task nos in a group
        return [task_no for task_no in cls.tasks if cls.tasks[task_no][1] == group]

    @classmethod
    def _get_group(cls, task_no):  # Return group given a task_no
        return cls.tasks[task_no][1]

    @classmethod
    def _stopped(cls, task_no):
        if task_no in cls.tasks:
            barrier = cls.tasks[task_no][2]
            if barrier is not None:  # Cancellation in progress
                barrier.trigger()
            del cls.tasks[task_no]

    def __init__(self, gf, *args, group=0, **kwargs):
        task = gf(TaskId(Cancellable.task_no), *args, **kwargs)
        if task in self.tasks:
            raise ValueError('Task already exists.')
        self.tasks[Cancellable.task_no] = [task, group, None]
        self.task_no = Cancellable.task_no  # For subclass
        Cancellable.task_no += 1
        self.task = task

    def __call__(self):
        return self.task

    def __await__(self):  # Return any value returned by task.
        return (yield from self.task)

    __iter__ = __await__


# @cancellable decorator

def cancellable(f):
    def new_gen(*args, **kwargs):
        if isinstance(args[0], TaskId):  # Not a bound method
            task_id = args[0]
            g = f(*args[1:], **kwargs)
        else:  # Task ID is args[1] if a bound method
            task_id = args[1]
            args = (args[0],) + args[2:]
            g = f(*args, **kwargs)
        try:
            res = await g
            return res
        finally:
            NamedTask._stopped(task_id)
    return new_gen

# The NamedTask class enables a coro to be identified by a user defined name.
# It constrains Cancellable to allow groups of one coro only.
# It maintains a dict of barriers indexed by name.
class NamedTask(Cancellable):
    instances = {}

    @classmethod
    async def cancel(cls, name, nowait=True):
        if name in cls.instances:
            await cls.cancel_all(group=name, nowait=nowait)
            return True
        return False

    @classmethod
    def is_running(cls, name):
        return cls._is_running(group=name)

    @classmethod
    def _stopped(cls, task_id):  # On completion remove it
        name = cls._get_group(task_id())  # Convert task_id to task_no
        if name in cls.instances:
            instance = cls.instances[name]
            barrier = instance.barrier
            if barrier is not None:
                barrier.trigger()
            del cls.instances[name]
        Cancellable._stopped(task_id())

    def __init__(self, name, gf, *args, barrier=None, **kwargs):
        if name in self.instances:
            raise ValueError('Task name "{}" already exists.'.format(name))
        super().__init__(gf, *args, group=name, **kwargs)
        self.barrier = barrier
        self.instances[name] = self


# @namedtask
namedtask = cancellable  # compatibility with old code

# Condition class

class Condition():
    def __init__(self, lock=None):
        self.lock = Lock() if lock is None else lock
        self.events = []

    async def acquire(self):
        await self.lock.acquire()

# enable this syntax:
# with await condition [as cond]:
    def __await__(self):
        yield from self.lock.acquire()
        return self

    __iter__ = __await__

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.lock.release()

    def locked(self):
        return self.lock.locked()

    def release(self):
        self.lock.release()  # Will raise RuntimeError if not locked

    def notify(self, n=1):  # Caller controls lock
        if not self.lock.locked():
            raise RuntimeError('Condition notify with lock not acquired.')
        for _ in range(min(n, len(self.events))):
            ev = self.events.pop()
            ev.set()

    def notify_all(self):
        self.notify(len(self.events))

    async def wait(self):
        if not self.lock.locked():
            raise RuntimeError('Condition wait with lock not acquired.')
        ev = Event()
        self.events.append(ev)
        self.lock.release()
        await ev
        await self.lock.acquire()
        assert ev not in self.events, 'condition wait assertion fail'
        return True  # CPython compatibility

    async def wait_for(self, predicate):
        result = predicate()
        while not result:
            await self.wait()
            result = predicate()
        return result

# Provide functionality similar to asyncio.gather()

class Gather():
    def __init__(self, gatherables):
        ncoros = len(gatherables)
        self.barrier = Barrier(ncoros + 1)
        self.results = [None] * ncoros
        loop = asyncio.get_event_loop()
        for n, gatherable in enumerate(gatherables):
            loop.create_task(self.wrap(gatherable, n)())

    def __iter__(self):
        yield from self.barrier.__await__()
        return self.results

    def wrap(self, gatherable, idx):
        async def wrapped():
            coro, args, kwargs = gatherable()
            try:
                tim = kwargs.pop('timeout')
            except KeyError:
                self.results[idx] = await coro(*args, **kwargs)
            else:
                self.results[idx] = await asyncio.wait_for(coro(*args, **kwargs), tim)
            self.barrier.trigger()
        return wrapped

class Gatherable():
    def __init__(self, coro, *args, **kwargs):
        self.arguments = coro, args, kwargs

    def __call__(self):
        return self.arguments
