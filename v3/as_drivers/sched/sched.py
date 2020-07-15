# sched.py

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
from sched.primitives import launch
from time import time

async def schedule(fcron, routine, args=(), run_once=False):
    maxt = 1000  # uasyncio can't handle arbitrarily long delays
    done = False
    while not done:
        tw = fcron(int(time()))  # Time to wait (s)
        while tw > 0:  # While there is still time to wait
            tw = min(tw, maxt)
            await asyncio.sleep(tw)
            tw -= maxt
        launch(routine, args)
        done = run_once
        await asyncio.sleep_ms(1200)  # ensure we're into next second
