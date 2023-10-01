# __init__.py Common functions for uasyncio threadsafe primitives

# Copyright (c) 2022 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

_attrs = {
    "ThreadSafeEvent": "threadsafe_event",
    "ThreadSafeQueue": "threadsafe_queue",
    "Message": "message",
    "Context": "context",
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
