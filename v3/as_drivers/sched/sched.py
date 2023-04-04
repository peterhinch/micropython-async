# sched.py

# Copyright (c) 2020-2023 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

import uasyncio as asyncio
from sched.primitives import launch
from time import time, mktime, localtime
from sched.cron import cron


# uasyncio can't handle long delays so split into 1000s (1e6 ms) segments
_MAXT = const(1000)
# Wait prior to a sequence start
_PAUSE = const(2)

async def schedule(func, *args, times=None, **kwargs):
    async def long_sleep(t):  # Sleep with no bounds. Immediate return if t < 0.
        while t > 0:
            await asyncio.sleep(min(t, _MAXT))
            t -= _MAXT

    tim = mktime(localtime()[:3] + (0, 0, 0, 0, 0))  # Midnight last night
    now = round(time())  # round() is for Unix
    fcron = cron(**kwargs)  # Cron instance for search.
    while tim < now:  # Find first event in sequence
        # Defensive. fcron should never return 0, but if it did the loop would never quit
        tim += max(fcron(tim), 1)
    await long_sleep(tim - now - _PAUSE) # Time to wait (can be < 0)

    while times is None or times > 0:
        tw = fcron(round(time()))  # Time to wait (s)
        await long_sleep(tw)
        if isinstance(func, asyncio.Event):
            func.set()
        else:
            res = launch(func, args)
        if times is not None:
            times -= 1
        await asyncio.sleep_ms(1200)  # ensure we're into next second
    return res
