# overdue.py Test for "low priority" uasyncio. Author Peter Hinch April 2017.
# overdue.test(1000) the low priority task should run once per second.
# overdue.test() scheduler uses normal algo. High priority task hogs
# scheduler because it never issues a nonzero delay.

import uasyncio as asyncio
ntimes = 0

async def lp_task():
    global ntimes
    while True:
        await asyncio.after_ms(100)
        print('LP task runs.')
        ntimes += 1

async def hp_task():  # Hog the scheduler
    while True:
        await asyncio.sleep_ms(0)

async def end():
    print('Test runs for 10 secs...')
    await asyncio.sleep(10)
    print('Low priority coro was scheduled {} times.'.format(ntimes))

def test(overdue_schedule=None):
    loop = asyncio.get_event_loop()
    if overdue_schedule is not None:
        loop.max_overdue_ms(overdue_schedule)
    loop.create_task(hp_task())
    loop.create_task(lp_task())
    loop.run_until_complete(end())

print('Issue overdue.test(1000) to demo overdue feature of low priority (LP) task.')
print('overdue.test() shows LP task never getting execution owing to greedy high priority task.')
