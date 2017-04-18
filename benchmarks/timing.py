# timing.py Benchmark for uasyncio. Author Peter Hinch April 2017.

# This measures the accuracy of uasyncio.sleep_ms() in the presence of a number of
# other coros. This tests (and therefore requires) the version of core.py which
# incorporates the priority mechanism (in parent directory).

# Outcome: when the priority mechanism is used the worst-case 10ms delay was 11.9ms
# for all numbers of coros. This occurs when the 10ms delay elapses immediately
# after foo() was scheduled - foo() must run to completion, taking 2ms, before
# the priority() can be re-scheduled.
# For 200 coros the 10ms delay takes 9.7-10.2ms.

# With the normal algorithm the 10ms delay takes ~N*Dms where N is the number of
# foo() instances and D is foo's processing delay (2ms).
# So for 200 coros the 10ms delay takes 398-408ms.

# TEST state after adding gc
# With priority get times of up to 14.6ms when I expected 12ms
# Without get results like
# Coros  100  t = 207.8ms min 210.8ms max sd 198.19ms
# Are these correct and why is sd low?

import uasyncio as asyncio
import pyb
import utime as time
import gc

# Determine version of core.py
low_priority = asyncio.low_priority if 'low_priority' in dir(asyncio) else None

num_coros = (5, 10, 100, 200)
duration = 2  # Time to run for each number of coros
done = False

tmax = 0
tmin = 1000000
dtotal = 0
count = 0
lst_tmax = [tmax] * len(num_coros)
lst_tmin = [tmin] * len(num_coros)
lst_sd = [0] * len(num_coros)

async def report(target_delay):
    while not done:
        await asyncio.sleep(1)
    print('Nominal delay of priority task was {}ms.'.format(target_delay))
    for x, n in enumerate(num_coros):
        print('Coros {:4d}  Actual delay = {:5.1f}ms min. {:5.1f}ms max. {:5.1f}ms avg.'.format(
            n, lst_tmin[x] / 1000, lst_tmax[x] /1000, lst_sd[x] / 1000))

async def lp_task(delay):
    yield low_priority  # If running low priority get on LP queue ASAP
    while True:
        time.sleep_ms(delay)  # Simulate processing
        yield low_priority

async def priority(ms):
    global tmax, tmin, dtotal, count
    while True:
        tstart = time.ticks_us()
        await asyncio.sleep_ms(ms)  # Measure the actual delay
        delta = time.ticks_diff(time.ticks_us(), tstart)
        tmax = max(tmax, delta)
        tmin = min(tmin, delta)
        dtotal += delta
        count += 1

async def run_test(delay, ms_delay):
    global done, tmax, tmin, dtotal, count
    print('Testing accuracy of {}ms nominal delay with coros blocking for {}ms.'.format(ms_delay, delay))
    if low_priority is None:
        print('Not using priority mechanism.')
    else:
        print('Using priority mechanism.')
    loop = asyncio.get_event_loop(max(num_coros) + 3)
    loop.create_task(priority(ms_delay))
    old_n = 0
    for n, n_coros in enumerate(num_coros):
        print('{:4d} coros. Test for {}s'.format(n_coros, duration))
        for _ in range(n_coros - old_n):
            loop.create_task(lp_task(delay))
        await asyncio.sleep(1)  # ensure tasks are all on LP queue before we measure
        gc.collect()  # ensure it doesn't cloud the issue
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
    global low_priority
    target_delay = 10  # Nominal delay in priority task (ms)
    processing_delay = 2  # Processing time in low priority task (ms)
    if use_priority and low_priority is None:
        print('To test priority mechanism you must use the modified core.py')
    else:
        if use_priority:
            loop = asyncio.get_event_loop(max(num_coros) + 3, max(num_coros))
        else:
            low_priority = None
            loop = asyncio.get_event_loop(max(num_coros) + 3)
        loop.create_task(run_test(processing_delay, target_delay))
        loop.run_until_complete(report(target_delay))

print('Issue timing.test() to test priority mechanism, timing.test(False) to test standard algo.')

