# __init__.py Common functions for uasyncio primitives

# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


async def _g():
    pass
type_coro = type(_g())

# If a callback is passed, run it and return.
# If a coro is passed initiate it and return.
# coros are passed by name i.e. not using function call syntax.
def launch(func, tup_args):
    res = func(*tup_args)
    if isinstance(res, type_coro):
        res = asyncio.create_task(res)
    return res

def set_global_exception():
    def _handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        sys.exit()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_handle_exception)

async def wait_any(events):
    evt = asyncio.Event()
    trig_event = None
    async def wt(event):
        nonlocal trig_event
        await event.wait()
        evt.set()
        trig_event = event
    tasks = [asyncio.create_task(wt(event)) for event in events]
    await evt.wait()
    for task in tasks:
        task.cancel()
    return trig_event

_attrs = {
    "AADC": "aadc",
    "Barrier": "barrier",
    "Condition": "condition",
    "Delay_ms": "delay_ms",
    "Encode": "encoder_async",
    "Message": "message",
    "Pushbutton": "pushbutton",
    "ESP32Touch": "pushbutton",
    "Queue": "queue",
    "Semaphore": "semaphore",
    "BoundedSemaphore": "semaphore",
    "Switch": "switch",
}

# Copied from uasyncio.__init__.py
# Lazy loader, effectively does:
#   global attr
#   from .mod import attr
def __getattr__(attr):
    mod = _attrs.get(attr, None)
    if mod is None:
        raise AttributeError(attr)
    value = getattr(__import__(mod, None, None, True, 1), attr)
    globals()[attr] = value
    return value
