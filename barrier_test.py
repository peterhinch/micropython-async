import uasyncio as asyncio
from asyn import Barrier

async def killer(duration):
    await asyncio.sleep(duration)

def callback(text):
    print(text)

barrier = Barrier(3, callback, ('Synch',))

async def speak():
    for i in range(5):
        print('{} '.format(i), end='')
        await barrier.signal_and_wait()

loop = asyncio.get_event_loop()
loop.create_task(speak())
loop.create_task(speak())
loop.create_task(speak())
loop.run_until_complete(killer(2))
loop.close()

