# sched.py

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
from sched.primitives import launch
from time import time
from sched.cron import cron

async def schedule(func, *args, times=None, **kwargs):
    fcron = cron(**kwargs)
    maxt = 1000  # uasyncio can't handle arbitrarily long delays
    while times is None or times > 0:
        tw = fcron(int(time()))  # Time to wait (s)
        while tw > 0:  # While there is still time to wait
            await asyncio.sleep(min(tw, maxt))
            tw -= maxt
        res = launch(func, args)
        if times is not None:
            times -= 1
        await asyncio.sleep_ms(1200)  # ensure we're into next second
    return res
