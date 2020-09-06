# cantest.py Tests of task cancellation

# The MIT License (MIT)
#
# Copyright (c) 2017-2018 Peter Hinch
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
import asyn
import utime as time

def print_tests():
    st = '''Available functions:
test1()  Basic NamedTask cancellation.
test2()  Use of Barrier to synchronise NamedTask cancellation. Demo of latency.
test3()  Cancellation of a NamedTask which has run to completion.
test4()  Test of Cancellable class.
test5()  Cancellable and NamedTask instances as bound methods.
test6()  Test of NamedTask.is_running() and awaiting NamedTask cancellation.
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

@asyn.cancellable
async def foo(num):
    try:
        await asyncio.sleep(4)
    except asyn.StopTask:
        print('foo was cancelled.')
        return -1
    else:
        return num + 42

async def kill(task_name):
    res = await asyn.NamedTask.cancel(task_name)
    if res: 
        print(task_name, 'will be cancelled when next scheduled')
    else:
        print(task_name, 'was not cancellable.')

# Example of a task which cancels another
async def bar():
    await asyncio.sleep(1)
    await kill('foo')
    await kill('not me')  # Will fail because not yet scheduled

async def run_cancel_test1():
    loop = asyncio.get_event_loop()
    loop.create_task(bar())
    res = await asyn.NamedTask('foo', foo, 5)
    print(res, asyn.NamedTask.is_running('foo'))
    res = await asyn.NamedTask('not me', foo, 0)  # Runs to completion
    print(res, asyn.NamedTask.is_running('not me'))

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

# Intercepting the StopTask exception.
@asyn.cancellable
async def rats(n):
    try:
        await forever(n)
    except asyn.StopTask:
        print('Instance', n, 'was cancelled')

async def run_cancel_test2():
    barrier = asyn.Barrier(3)
    loop = asyncio.get_event_loop()
    loop.create_task(asyn.NamedTask('rats_1', rats, 1, barrier=barrier)())
    loop.create_task(asyn.NamedTask('rats_2', rats, 2, barrier=barrier)())
    print('Running two tasks')
    await asyncio.sleep(10)
    print('About to cancel tasks')
    await asyn.NamedTask.cancel('rats_1')  # These will stop when their wait is complete
    await asyn.NamedTask.cancel('rats_2')
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

# Intercepting the StopTask exception.
@asyn.cancellable
async def cant3():
    try:
        await asyncio.sleep(1)
        print('Task cant3 has ended.')
    except asyn.StopTask:
        print('Task cant3 was cancelled')

async def run_cancel_test3():
    barrier = asyn.Barrier(2)
    loop = asyncio.get_event_loop()
    loop.create_task(asyn.NamedTask('cant3', cant3, barrier=barrier)())
    print('Task cant3 running status', asyn.NamedTask.is_running('cant3'))
    await asyncio.sleep(3)
    print('Task cant3 running status', asyn.NamedTask.is_running('cant3'))
    print('About to cancel task')
    await asyn.NamedTask.cancel('cant3')
    print('Cancelled')
    print('Task cant3 running status', asyn.NamedTask.is_running('cant3'))
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

@asyn.cancellable
async def cant40(num):
    while True:
        try:
            await asyn.sleep(1)
            print('Task cant40 no. {} running.'.format(num))
        except asyn.StopTask:
            print('Task cant40 no. {} was cancelled'.format(num))
            return

@asyn.cancellable
async def cant41(num, arg=0):
    try:
        await asyn.sleep(1)
        print('Task cant41 no. {} running, arg {}.'.format(num, arg))
    except asyn.StopTask:
        print('Task cant41 no. {} was cancelled.'.format(num))
        return
    else:
        print('Task cant41 no. {} ended.'.format(num))

async def cant42(num):
    while True:
        print('Task cant42 no. {} running'.format(num))
        await asyn.sleep(1.2)

# Test await syntax and throwing exception to subtask
@asyn.cancellable
async def chained(num, x, y, *, red, blue):
    print('Args:', x, y, red, blue)  # Test args and kwargs
    try:
        await cant42(num)
    except asyn.StopTask:
        print('Task chained no. {} was cancelled'.format(num))

async def run_cancel_test4():
    await asyn.Cancellable(cant41, 0, 5)
    loop = asyncio.get_event_loop()
    loop.create_task(asyn.Cancellable(cant40, 1)())  # 3 instances in default group 0
    loop.create_task(asyn.Cancellable(cant40, 2)())
    loop.create_task(asyn.Cancellable(cant40, 3)())
    loop.create_task(asyn.Cancellable(chained, 4, 1, 2, red=3, blue=4, group=1)())
    loop.create_task(asyn.Cancellable(cant41, 5)())  # Runs to completion
    print('Running tasks')
    await asyncio.sleep(3)
    print('About to cancel group 0 tasks')
    await asyn.Cancellable.cancel_all()  # All in default group 0
    print('Group 0 tasks were cancelled')
    await asyncio.sleep(1)  # Demo chained still running
    print('About to cancel group 1 tasks')
    await asyn.Cancellable.cancel_all(1)  # Group 1
    print('Group 1 tasks were cancelled')
    await asyncio.sleep(1)

def test4():
    printexp('''Task cant41 no. 0 running, arg 5.
Task cant41 no. 0 ended.
Running tasks
Args: 1 2 3 4
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
        loop.create_task(asyn.Cancellable(self.foo, 1)())  # 3 instances in default group 0
        loop.create_task(asyn.Cancellable(self.foo, 2)())
        loop.create_task(asyn.Cancellable(self.foo, 3)())
        loop.create_task(asyn.NamedTask('my bar', self.bar, 4, y=42)())
        await asyncio.sleep(4.5)
        await asyn.NamedTask.cancel('my bar')
        await asyn.Cancellable.cancel_all()
        await asyncio.sleep(1)
        print('Done')

    @asyn.cancellable
    async def foo(self, arg):
        try:
            while True:
                await asyn.sleep(1)
                print('foo running, arg', arg)
        except asyn.StopTask:
            print('foo was cancelled')

    @asyn.cancellable
    async def bar(self, arg, *, x=1, y=2):
        try:
            while True:
                await asyn.sleep(1)
                print('bar running, arg', arg, x, y)
        except asyn.StopTask:
            print('bar was cancelled')

def test5():
    printexp('''foo running, arg 1
foo running, arg 2
foo running, arg 3
bar running, arg 4 1 42
foo running, arg 1
foo running, arg 2
foo running, arg 3
bar running, arg 4 1 42
foo running, arg 1
foo running, arg 2
foo running, arg 3
bar running, arg 4 1 42
foo running, arg 1
foo running, arg 2
foo running, arg 3
bar running, arg 4 1 42
foo was cancelled
foo was cancelled
foo was cancelled
bar was cancelled
Done
''', 6)
    cantest = CanTest()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(cantest.start(loop))

# test 6: test NamedTask.is_running()
@asyn.cancellable
async def cant60(name):
    print('Task cant60 name \"{}\" running.'.format(name))
    try:
        for _ in range(5):
            await asyncio.sleep(2)  # 2 secs latency.
    except asyn.StopTask:
        print('Task cant60 name \"{}\" was cancelled.'.format(name))
        return
    else:
        print('Task cant60 name \"{}\" ended.'.format(name))

@asyn.cancellable
async def cant61():
    try:
        while True:
            for name in ('complete', 'cancel me'):
                res = asyn.NamedTask.is_running(name)
                print('Task \"{}\" running: {}'.format(name, res))
            await asyncio.sleep(1)
    except asyn.StopTask:
        print('Task cant61 cancelled.')

async def run_cancel_test6(loop):
    for name in ('complete', 'cancel me'):
        loop.create_task(asyn.NamedTask(name, cant60, name)())
    loop.create_task(asyn.Cancellable(cant61)())
    await asyncio.sleep(4.5)
    print('Cancelling task \"{}\". 1.5 secs latency.'.format(name))
    await asyn.NamedTask.cancel(name)
    await asyncio.sleep(7)
    name = 'cancel wait'
    loop.create_task(asyn.NamedTask(name, cant60, name)())
    await asyncio.sleep(0.5)
    print('Cancelling task \"{}\". 1.5 secs latency.'.format(name))
    t = time.ticks_ms()
    await asyn.NamedTask.cancel('cancel wait', nowait=False)
    print('Was cancelled in {} ms'.format(time.ticks_diff(time.ticks_ms(), t)))
    print('Cancelling cant61')
    await asyn.Cancellable.cancel_all()
    print('Done')


def test6():
    printexp('''Task cant60 name "complete" running.
Task cant60 name "cancel me" running.
Task "complete" running: True
Task "cancel me" running: True
Task "complete" running: True
Task "cancel me" running: True
Task "complete" running: True
Task "cancel me" running: True
Task "complete" running: True
Task "cancel me" running: True
Task "complete" running: True
Task "cancel me" running: True
Cancelling task "cancel me". 1.5 secs latency.
Task "complete" running: True
Task "cancel me" running: True
Task cant60 name "cancel me" was cancelled.
Task "complete" running: True
Task "cancel me" running: False
Task "complete" running: True
Task "cancel me" running: False
Task "complete" running: True
Task "cancel me" running: False
Task "complete" running: True
Task "cancel me" running: False
Task cant60 name "complete" ended.
Task "complete" running: False
Task "cancel me" running: False
Task "complete" running: False
Task "cancel me" running: False
Task cant60 name "cancel wait" running.
Cancelling task "cancel wait". 1.5 secs latency.
Task "complete" running: False
Task "cancel me" running: False
Task "complete" running: False
Task "cancel me" running: False
Task cant60 name "cancel wait" was cancelled.
Was cancelled in 1503 ms
Cancelling cant61
Task cant61 cancelled.
Done


[Duration of cancel wait may vary depending on platform 1500 <= range <= 1600ms]
''', 14)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test6(loop))
