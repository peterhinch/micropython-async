# overdue.py Test for "low priority" uasyncio. Author Peter Hinch April 2017.
import uasyncio as asyncio
try:
    if not(isinstance(asyncio.version, tuple)):
        raise AttributeError
except AttributeError:
    raise OSError('This program requires uasyncio fast_io version V0.24 or above.')

loop = asyncio.get_event_loop(lp_len=16)
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

async def report():
    global ntimes
    loop.max_overdue_ms(1000)
    loop.create_task(hp_task())
    loop.create_task(lp_task())
    print('First test runs for 10 secs. Max overdue time = 1s.')
    await asyncio.sleep(10)
    print('Low priority coro was scheduled {} times: (should be 9).'.format(ntimes))
    loop.max_overdue_ms(0)
    ntimes = 0
    print('Second test runs for 10 secs. Default scheduling.')
    print('Low priority coro should not be scheduled.')
    await asyncio.sleep(10)
    print('Low priority coro was scheduled {} times: (should be 0).'.format(ntimes))

loop = asyncio.get_event_loop()
loop.run_until_complete(report())

