# cantest.py Tests of task cancellation

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


import uasyncio as asyncio
from asyn import Barrier, NamedTask, StopTask, Cancellable, sleep, cancellable, namedtask

def print_tests():
    st = '''Available functions:
test1()  Basic NamedTask cancellation.
test2()  Use of Barrier to synchronise NamedTask cancellation.
test3()  Cancellation of a NamedTask which has run to completion.
test4()  Test of Cancellable class.
test5()  Cancellable and NamedTask instances as bound methods.
Recommended to issue ctrl-D after running each test.
'''
    print('\x1b[32m')
    print(st)
    print('\x1b[39m')

print_tests()

def printexp(exp, runtime=0):
    print('Expected output:')
    print('\x1b[32m')
    print(exp)
    print('\x1b[39m')
    if runtime:
        print('Running (runtime = {}s):'.format(runtime))
    else:
        print('Running (runtime < 1s):')

# cancel_test1()

@namedtask
async def foo(name, num):
    try:
        await asyncio.sleep(4)
        return num + 42
    except StopTask:
        print('foo was cancelled.')
        return -1

def kill(task_name):
    if NamedTask.cancel(task_name): 
        print(task_name, 'will be cancelled when next scheduled')
    else:
        print(task_name, 'was not cancellable.')

# Example of a task which cancels another
async def bar():
    await asyncio.sleep(1)
    kill('foo')
    kill('not me')  # Will fail because not yet scheduled

async def run_cancel_test1():
    loop = asyncio.get_event_loop()
    loop.create_task(bar())
    res = await NamedTask('foo', foo, 5)
    print(res, NamedTask.is_running('foo'))
    res = await NamedTask('not me', foo, 0)  # Runs to completion
    print(res, NamedTask.is_running('not me'))

def test1():
    printexp('''foo will be cancelled when next scheduled
not me was not cancellable.
foo was cancelled.
-1 False
42 False
''', 8)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test1())

# test2()
# This test uses a barrier so that cancelling task pauses until cancelled tasks
# have actually terminated. Also tests the propagation of the thrown exception
# to the awaiting coro.

async def forever(n):
    print('Started forever() instance', n)
    while True:
        await asyncio.sleep(7 + n)
        print('Running instance', n)

# Cancellable coros must trap the StopTask. If a barrier is used, coro must
# pass it whether cancelled or terminates normally.
@namedtask
async def rats(name, n):
    try:
        await forever(n)
    except StopTask:
        print('Instance', n, 'was cancelled')

async def run_cancel_test2():
    barrier = Barrier(3)
    loop = asyncio.get_event_loop()
    loop.create_task(NamedTask('rats_1', rats, 1, barrier=barrier)())
    loop.create_task(NamedTask('rats_2', rats, 2, barrier=barrier)())
    print('Running two tasks')
    await asyncio.sleep(10)
    print('About to cancel tasks')
    NamedTask.cancel('rats_1')  # These will stop when their wait is complete
    NamedTask.cancel('rats_2')
    await barrier  # So wait for that to occur.
    print('tasks were cancelled')

def test2():
    printexp('''Running two tasks
Started forever() instance 1
Started forever() instance 2
Running instance 1
Running instance 2
About to cancel tasks
Instance 1 was cancelled
Instance 2 was cancelled
tasks were cancelled
''', 20)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test2())

# test3()
# Test of cancelling a task which has already terminated

# Cancellable coros must trap the StopTask
@namedtask
async def cant3(name):
    try:
        await asyncio.sleep(1)
        print('Task cant3 has ended.')
    except StopTask:
        print('Task cant3 was cancelled')

async def run_cancel_test3():
    barrier = Barrier(2)
    loop = asyncio.get_event_loop()
    loop.create_task(NamedTask('cant3', cant3, barrier=barrier)())
    print('Task cant3 running status', NamedTask.is_running('cant3'))
    await asyncio.sleep(3)
    print('Task cant3 running status', NamedTask.is_running('cant3'))
    print('About to cancel task')
    NamedTask.cancel('cant3')
    print('Cancelled')
    print('Task cant3 running status', NamedTask.is_running('cant3'))
    await barrier
    print('tasks were cancelled')

def test3():
    printexp('''Task cant3 running status True
Task cant3 has ended.
Task cant3 running status False
About to cancel task
Cancelled
Task cant3 running status False
tasks were cancelled
''', 3)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test3())

# test4()
# Test of cancelling a task which has already terminated

# Cancellable coros can trap the StopTask. They are passed the
# task_id automatically

@cancellable
async def cant40(task_id):
    task_no = task_id()
    while True:
        try:
            await sleep(1)
            print('Task cant40 no. {} running.'.format(task_no))
        except StopTask:
            print('Task cant40 no. {} was cancelled'.format(task_no))
            raise

@cancellable
async def cant41(task_id, arg=0):
    task_no = task_id()
    try:
        await sleep(1)
        print('Task cant41 no. {} running, arg {}.'.format(task_no, arg))
    except StopTask:
        print('Task cant41 no. {} was cancelled.'.format(task_no))
        raise
    else:
        print('Task cant41 no. {} ended.'.format(task_no))

async def cant42(task_no):
    while True:
        print('Task cant42 no. {} running'.format(task_no))
        await sleep(1.2)

# Test await syntax and throwing exception to subtask
@cancellable
async def chained(task_id):
    task_no = task_id()
    try:
        await cant42(task_no)
    except StopTask:
        print('Task chained no. {} was cancelled'.format(task_no))
        raise

async def run_cancel_test4():
    await Cancellable(cant41, 5)
    loop = asyncio.get_event_loop()
    loop.create_task(Cancellable(cant40)())  # 3 instances in default group 0
    loop.create_task(Cancellable(cant40)())
    loop.create_task(Cancellable(cant40)())
    loop.create_task(Cancellable(chained, group=1)())
    loop.create_task(Cancellable(cant41)())  # Runs to completion
    print('Running tasks')
    await asyncio.sleep(3)
    print('About to cancel group 0 tasks')
    await Cancellable.cancel_all()  # All in default group 0
    print('Group 0 tasks were cancelled')
    await asyncio.sleep(1)  # Demo chained still running
    print('About to cancel group 1 tasks')
    await Cancellable.cancel_all(1)  # Group 1
    print('Group 1 tasks were cancelled')
    await asyncio.sleep(1)

def test4():
    printexp('''Task cant41 no. 0 running, arg 5.
Task cant41 no. 0 ended.
Running tasks
Task cant42 no. 4 running
Task cant40 no. 1 running.
Task cant40 no. 2 running.
Task cant40 no. 3 running.
Task cant41 no. 5 running, arg 0.
Task cant41 no. 5 ended.
Task cant42 no. 4 running
Task cant40 no. 1 running.
Task cant40 no. 2 running.
Task cant40 no. 3 running.
Task cant42 no. 4 running
About to cancel group 0 tasks
Task cant40 no. 1 was cancelled
Task cant40 no. 2 was cancelled
Task cant40 no. 3 was cancelled
Group 0 tasks were cancelled
Task cant42 no. 4 running
About to cancel group 1 tasks
Task chained no. 4 was cancelled
Group 1 tasks were cancelled
''', 6)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test4())

# test5
# Test of task cancellation where tasks are bound methods

class CanTest():
    async def start(self, loop):
        loop.create_task(Cancellable(self.foo, 1)())  # 3 instances in default group 0
        loop.create_task(Cancellable(self.foo, 2)())
        loop.create_task(Cancellable(self.foo, 3)())
        loop.create_task(NamedTask('my bar', self.bar, 4)())
        await asyncio.sleep(4.5)
        NamedTask.cancel('my bar')
        await Cancellable.cancel_all()
        await asyncio.sleep(1)
        print('Done')

    @cancellable
    async def foo(self, _, arg):
        try:
            while True:
                await sleep(1)
                print('foo running, arg', arg)
        except StopTask:
            print('foo was cancelled')
            raise

    @namedtask
    async def bar(self, _, arg):
        try:
            while True:
                await sleep(1)
                print('bar running, arg', arg)
        except StopTask:
            print('bar was cancelled')

def test5():
    printexp('''foo running, arg 1
foo running, arg 2
foo running, arg 3
bar running, arg 4
foo running, arg 1
foo running, arg 2
foo running, arg 3
bar running, arg 4
foo running, arg 1
foo running, arg 2
foo running, arg 3
bar running, arg 4
foo running, arg 1
foo running, arg 2
foo running, arg 3
bar running, arg 4
foo was cancelled
foo was cancelled
foo was cancelled
bar was cancelled
Done
''', 6)
    cantest = CanTest()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(cantest.start(loop))
