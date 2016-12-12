import uasyncio as asyncio
from asyn import Event

async def eventwait(event, ack_event, n):
    await event.wait()
    print('Eventwait {} got event.'.format(n))
    ack_event.set()

async def foo():
    loop = asyncio.get_event_loop()
    event = Event()
    ack1 = Event()
    ack2 = Event()
    while True:
        loop.create_task(eventwait(event, ack1, 1))
        loop.create_task(eventwait(event, ack2, 2))
        event.set()
        print('event was set')
        await ack1.wait()
        ack1.clear()
        print('Cleared ack1')
        await ack2.wait()
        ack2.clear()
        print('Cleared ack2')
        event.clear()
        print('Cleared event')
        await asyncio.sleep(1)

async def main(delay):
    await asyncio.sleep(delay)
    print("I've seen starships burn off the shoulder of Orion...")
    print("Time to die...")

loop = asyncio.get_event_loop()
loop.create_task(foo())
loop.run_until_complete(main(10))
