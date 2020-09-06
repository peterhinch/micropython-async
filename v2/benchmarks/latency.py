# latency.py Benchmark for uasyncio. Author Peter Hinch July 2018.

# This measures the scheduling latency of a notional device driver running in the
# presence of other coros. This can test asyncio_priority.py which incorporates
# the priority mechanism. (In the home directory of this repo).

# When running the test that uses the priority mechanism the latency is 300us which
# is determined by the time it takes uasyncio to schedule a coro (see rate.py).
# This is because, when the priority() coro issues await device it is the only coro
# on the normal queue and it therefore is immediately scheduled.

# When running the test without the priority mechanism, the latency is D*Nms where N
# is the number of instances of the foo() coro and D is the processing period of
# foo() in ms (2). This is because priority() will only be rescheduled after every
# foo() instance has run.

# For compute-intensive tasks a yield every 2ms is reasonably efficient. A shorter
# period implies a significant proportion of CPU cycles being taken up in scheduling.

import uasyncio as asyncio
lp_version = True
try:
    if not(isinstance(asyncio.version, tuple)):
        raise AttributeError
except AttributeError:
    lp_version = False

import pyb
import utime as time
import gc

num_coros = (5, 10, 100, 200)
duration = 2  # Time to run for each number of coros
done = False

tmax = 0
tmin = 1000000
dtotal = 0
count = 0
lst_tmax = [tmax] * len(num_coros)  # Max, min and avg error values
lst_tmin = [tmin] * len(num_coros)
lst_sd = [0] * len(num_coros)

class DummyDeviceDriver():
    def __iter__(self):
        yield

async def report():
    # Don't compromise results by executing too soon. Time round loop is duration + 1
    await after(1 + len(num_coros) * (duration + 1))
    print('Awaiting result...')
    while not done:
        await after_ms(1000)
    s = 'Coros {:4d} Latency = {:6.2f}ms min. {:6.2f}ms max. {:6.2f}ms avg.'
    for x, n in enumerate(num_coros):
        print(s.format(n, lst_tmin[x] / 1000, lst_tmax[x] /1000, lst_sd[x] / 1000))

async def lp_task(delay):
    await after_ms(0)  # If running low priority get on LP queue ASAP
    while True:
        time.sleep_ms(delay)  # Simulate processing
        await after_ms(0)

async def priority():
    global tmax, tmin, dtotal, count
    device = DummyDeviceDriver()
    while True:
        await after(0)  # Ensure low priority coros get to run
        tstart = time.ticks_us()
        await device  # Measure the latency
        delta = time.ticks_diff(time.ticks_us(), tstart)
        tmax = max(tmax, delta)
        tmin = min(tmin, delta)
        dtotal += delta
        count += 1

async def run_test(delay):
    global done, tmax, tmin, dtotal, count
    loop.create_task(priority())
    old_n = 0
    for n, n_coros in enumerate(num_coros):
        print('{:4d} coros. Test for {}s'.format(n_coros, duration))
        for _ in range(n_coros - old_n):
            loop.create_task(lp_task(delay))
        await asyncio.sleep(1)  # ensure tasks are all on LP queue before we measure
        gc.collect()  # ensure gc doesn't cloud the issue
        old_n = n_coros
        tmax = 0
        tmin = 1000000
        dtotal = 0
        count = 0
        await asyncio.sleep(duration)
        lst_tmin[n] = tmin
        lst_tmax[n] = tmax
        lst_sd[n] = dtotal / count
    done = True

def test(use_priority=True):
    global after, after_ms, loop, lp_version
    processing_delay = 2  # Processing time in low priority task (ms)
    if use_priority and not lp_version:
        print('To test priority mechanism you must use fast_io version of uasyncio.')
    else:
        ntasks = max(num_coros) + 10 #4
        if use_priority:
            loop = asyncio.get_event_loop(ntasks, ntasks, 0, ntasks)
            after = asyncio.after
            after_ms = asyncio.after_ms
        else:
            lp_version = False
            after = asyncio.sleep
            after_ms = asyncio.sleep_ms
            loop = asyncio.get_event_loop(ntasks, ntasks)
        s = 'Testing latency of priority task with coros blocking for {}ms.'
        print(s.format(processing_delay))
        if lp_version:
            print('Using priority mechanism.')
        else:
            print('Not using priority mechanism.')
        loop.create_task(run_test(processing_delay))
        loop.run_until_complete(report())

print('Issue latency.test() to test priority mechanism, latency.test(False) to test standard algo.')
