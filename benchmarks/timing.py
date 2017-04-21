# timing.py Benchmark for uasyncio. Author Peter Hinch April 2017.

# This measures the accuracy of uasyncio.sleep_ms() in the presence of a number of
# other coros. This can test the version of core.py which incorporates the priority
# mechanism. (In the home directory of this repo).

# Outcome: when the priority mechanism is used the worst-case 10ms delay was 11.93ms
# With the normal algorithm the 10ms delay takes ~N*Dms where N is the number of
# lp_task() instances and D is the lp_task() processing delay (2ms).
# So for 200 coros the 10ms delay takes up to 411ms.


import uasyncio as asyncio
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
lst_tmax = [tmax] * len(num_coros)
lst_tmin = [tmin] * len(num_coros)
lst_sd = [0] * len(num_coros)

async def report(target_delay):
    # Don't compromise results by executing too soon. Time round loop is duration + 1
    await after(1 + len(num_coros) * (duration + 1))
    print('Awaiting result...')
    while not done:
        await after_ms(1000)
    print('Nominal delay of priority task was {}ms.'.format(target_delay))
    s = 'Coros {:4d}  Actual delay = {:6.2f}ms min. {:6.2f}ms max. {:6.2f}ms avg.'
    for x, n in enumerate(num_coros):
        print(s.format(n, lst_tmin[x] / 1000, lst_tmax[x] /1000, lst_sd[x] / 1000))

async def lp_task(delay):
    await after_ms(0)  # If running low priority get on LP queue ASAP
    while True:
        time.sleep_ms(delay)  # Simulate processing
        await after_ms(0)  # LP yield

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
    loop = asyncio.get_event_loop()
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
    global after, after_ms
    target_delay = 10  # Nominal delay in priority task (ms)
    processing_delay = 2  # Processing time in low priority task (ms)
    lp_version = 'after' in dir(asyncio)
    if use_priority and not lp_version:
        print('To test priority mechanism you must use the modified core.py')
    else:
        ntasks = max(num_coros) + 4
        if use_priority:
            loop = asyncio.get_event_loop(ntasks, ntasks)
            after = asyncio.after
            after_ms = asyncio.after_ms
        else:
            lp_version = False
            after = asyncio.sleep
            after_ms = asyncio.sleep_ms
            loop = asyncio.get_event_loop(ntasks)
        s = 'Testing accuracy of {}ms nominal delay with coros blocking for {}ms.'
        print(s.format(target_delay, processing_delay))
        if lp_version:
            print('Using priority mechanism.')
        else:
            print('Not using priority mechanism.')
        loop.create_task(run_test(processing_delay, target_delay))
        loop.run_until_complete(report(target_delay))

print('Issue timing.test() to test priority mechanism, timing.test(False) to test standard algo.')
