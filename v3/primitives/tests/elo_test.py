# elo_test.py Test ELO class

# Copyright (c) 2024 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# from primitives.tests.elo_test import test
# test()

import asyncio
from primitives import WaitAny, WaitAll, ELO

evt = asyncio.Event()


def set_after(t):
    async def ta(t):
        await asyncio.sleep(t)
        print("set")
        evt.set()
        evt.clear()

    asyncio.create_task(ta(t))


def can_after(elo, t):
    async def ca(elo, t):
        await asyncio.sleep(t)
        elo().cancel()

    asyncio.create_task(ca(elo, t))


async def foo(t, n=42):
    await asyncio.sleep(t)
    return n


async def main():
    txt = """\x1b[32m
Expected output:

Test cancellation.
Canned
Test return of value.
Result: 42
Instantiate with running task
Result: 99
Delayed return of value.
Result: 88
\x1b[39m
"""
    print(txt)
    entries = (evt, elo := ELO(foo, 5))
    print("Test cancellation.")
    can_after(elo, 1)
    await WaitAny(entries).wait()
    task = elo()
    if isinstance(task, asyncio.CancelledError):
        print("Canned")

    print("Test return of value.")
    entries = (evt, elo := ELO(foo, 5))
    await WaitAny(entries).wait()
    res = await elo()
    print(f"Result: {res}")

    print("Instantiate with running task")
    elo = ELO(task := asyncio.create_task(foo(3, 99)))
    await WaitAny((elo, evt)).wait()
    res = await task
    print(f"Result: {res}")

    print("Delayed return of value.")
    entries = (evt, elo := ELO(foo, 5, 88))
    await WaitAny(entries).wait()
    set_after(1)  # Early exit
    res = await elo()  # Pause until complete
    print(f"Result: {res}")


def tests():
    txt = """
\x1b[32m
Issue:
from primitives.tests.elo_test import test
test()
\x1b[39m
"""
    print(txt)


def test():
    try:
        asyncio.run(main())
    finally:
        asyncio.new_event_loop()
        tests()


tests()
