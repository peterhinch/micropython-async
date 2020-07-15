# asynctest.py Demo of asynchronous code scheduling tasks with cron

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
from sched.sched import schedule
from sched.cron import cron
from time import localtime

def foo(txt):  # Demonstrate callback
    yr, mo, md, h, m, s, wd = localtime()[:7]
    fst = 'Callback {} {:02d}:{:02d}:{:02d} on {:02d}/{:02d}/{:02d}'
    print(fst.format(txt, h, m, s, md, mo, yr))

async def bar(txt):  # Demonstrate coro launch
    yr, mo, md, h, m, s, wd = localtime()[:7]
    fst = 'Coroutine {} {:02d}:{:02d}:{:02d} on {:02d}/{:02d}/{:02d}'
    print(fst.format(txt, h, m, s, md, mo, yr))
    await asyncio.sleep(0)

async def main():
    print('Asynchronous test running...')
    cron4 = cron(hrs=None, mins=range(0, 60, 4))
    asyncio.create_task(schedule(cron4, foo, ('every 4 mins',)))

    cron5 = cron(hrs=None, mins=range(0, 60, 5))
    asyncio.create_task(schedule(cron5, foo, ('every 5 mins',)))

    cron3 = cron(hrs=None, mins=range(0, 60, 3))  # Launch a coroutine
    asyncio.create_task(schedule(cron3, bar, ('every 3 mins',)))

    cron2 = cron(hrs=None, mins=range(0, 60, 2))
    asyncio.create_task(schedule(cron2, foo, ('one shot',), True))
    await asyncio.sleep(900)  # Quit after 15 minutes

try:
    asyncio.run(main())
finally:
    _ = asyncio.new_event_loop()
