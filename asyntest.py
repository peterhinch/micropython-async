import uasyncio as asyncio
from asyn import Lock, Event

async def bar(n, lock):
    print('bar {} waiting for lock'.format(n))
    async with lock:
        print('bar {} acquired lock'.format(n))
        await asyncio.sleep(1)  # Delay to demo other coros waiting for lock
    print('bar {} released lock'.format(n))

async def eventset(event):
    print('Waiting 5 secs before setting event')
    await asyncio.sleep(5)
    event.set()
    print('event was set')

async def eventwait(event):
    print('waiting for event')
    await event.wait()
    print('got event')
    event.clear()

async def main():
    print('Test Lock class')
    loop = asyncio.get_event_loop()
    lock = Lock()
    loop.create_task(bar(1, lock))
    loop.create_task(bar(2, lock))
    loop.create_task(bar(3, lock))
    print('Test Event class')
    event = Event()
    loop.create_task(eventset(event))
    await eventwait(event)  # main runs fast until this point
    print('Event status {}'.format(event.is_set()))
    print('Tasks complete')
    yield asyncio.StopLoop(loop)  # stop a loop started with run_forever()

loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
