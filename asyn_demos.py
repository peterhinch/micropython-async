# asyn_demos.py Simple demos of task cancellation
# Test/demo of official asyncio library and official Lock class

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
import asyn

def print_tests():
    st = '''Minimal demo programs of uasyncio task cancellation.
Issue ctrl-D to soft reset the board between test runs.
Available demos:
cancel_test()  Demo of Cancellable tasks.
named_test()  Demo of NamedTask.
method_test() Cancellable and NamedTask coros as bound methods.
'''
    print('\x1b[32m')
    print(st)
    print('\x1b[39m')

print_tests()

# Cancellable task minimal example
@asyn.cancellable
async def print_nums(num):
    while True:
        print(num)
        num += 1
        await asyn.sleep(1)

@asyn.cancellable
async def add_one(num):
    num += 1
    await asyn.sleep(1)
    return num

async def run_cancel_test(loop):
    res = await asyn.Cancellable(add_one, 41)
    print('Result: ', res)
    loop.create_task(asyn.Cancellable(print_nums, res)())
    await asyn.sleep(7.5)
    # Cancel any cancellable tasks still running
    await asyn.Cancellable.cancel_all()
    print('Done')

def cancel_test():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_cancel_test(loop))

# NamedTask minimal example

@asyn.cancellable
async def print_nums_named(num):
    while True:
        print(num)
        num += 1
        await asyn.sleep(1)

@asyn.cancellable
async def add_one_named(num):
    num += 1
    await asyn.sleep(1)
    return num

async def run_named_test(loop):
    res = await asyn.NamedTask('not cancelled', add_one_named, 99)
    print('Result: ', res)
    loop.create_task(asyn.NamedTask('print nums', print_nums_named, res)())
    await asyn.sleep(7.5)
    asyn.NamedTask.cancel('not cancelled')  # Nothing to do: task has finished
    asyn.NamedTask.cancel('print nums')  # Stop the continuously running task
    print('Done')

def named_test():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_named_test(loop))

# Tasks as bound methods

class CanDemo():
    async def start(self, loop):
        loop.create_task(asyn.Cancellable(self.foo, 1)())  # 3 instances in default group 0
        loop.create_task(asyn.Cancellable(self.foo, 2)())
        loop.create_task(asyn.Cancellable(self.foo, 3)())
        loop.create_task(asyn.NamedTask('my bar', self.bar, 4)())
        print('bar running status is', asyn.NamedTask.is_running('my bar'))
        await asyncio.sleep(4.5)
        await asyn.NamedTask.cancel('my bar')
        print('bar instance scheduled for cancellation.')
        await asyn.Cancellable.cancel_all()
        print('foo instances have been cancelled.')
        await asyncio.sleep(0.2)  # Allow for 100ms latency in bar()
        print('bar running status is', asyn.NamedTask.is_running('my bar'))
        print('Done')

    @asyn.cancellable
    async def foo(self, arg):
        while True:
            await asyn.sleep(1)
            print('foo running, arg', arg)

    @asyn.cancellable
    async def bar(self, arg):
        while True:
            await asyn.sleep(1)
            print('bar running, arg', arg)

def method_test():
    cantest = CanDemo()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(cantest.start(loop))
