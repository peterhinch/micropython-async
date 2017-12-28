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

print('''Minimal demo programs of uasyncio task cancellation.
Issue ctrl-D to soft reset the board between test runs.
Available demos:
cancel_test()  Demo of Cancellable tasks
named_test()  Demo of NamedTask
''')

# Cancellable task minimal example
@asyn.cancellable
async def print_nums(task_no, num):
    while True:
        print(num)
        num += 1
        await asyn.sleep(1)

@asyn.cancellable
async def add_one(task_no, num):
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

@asyn.namedtask
async def print_nums_named(name, num):
    while True:
        print(num)
        num += 1
        await asyn.sleep(1)

@asyn.namedtask
async def add_one_named(task_no, num):
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
