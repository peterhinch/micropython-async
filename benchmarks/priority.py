# priority.py Demonstrate high priority scheduling in modified uasyncio.
# Author Peter Hinch May 2017.

# Measures the maximum latency of a high priority task. This tests a flag set
# by a timer interrupt to ensure a realistic measurement. The "obvious" way,
# using a coro to set the flag, produces unrealistically optimistic results
# because the scheduler is started immediately after the flag is set.

try:
    import asyncio_priority as asyncio
except ImportError:
    print('This demo requires asyncio_priority.py')
import pyb
import utime as time
import gc
import micropython
micropython.alloc_emergency_exception_buf(100)

n_hp_tasks = 2          # Number of high priority tasks
n_tasks = 4             # Number of normal priority tasks

max_latency = 0         # Results: max latency of priority task
tmax = 0                # Latency of normal task
tmin = 1000000

class DummyDeviceDriver():
    def __iter__(self):
        yield

# boolean flag records time between setting and clearing it.
class Flag():
    def __init__(self):
        self.flag = False
        self.time_us = 0

    def __call__(self):
        return self.flag

    def set_(self):
        self.flag = True
        self.time_us = time.ticks_us()

    def clear(self):
        self.flag = False
        return time.ticks_diff(time.ticks_us(), self.time_us)

# Instantiate a flag for each priority task
flags = [Flag() for _ in range(n_hp_tasks)]

# Wait for a flag then clear it, updating global max_latency.
async def urgent(n):
    global max_latency
    flag = flags[n]
    while True:
        # Pause until flag is set. The callback is the bound method flag.__call__()
        await asyncio.when(flag)  # callback is passed not using function call syntax
        latency = flag.clear()  # Timer ISR has set the flag. Clear it.
        max_latency = max(max_latency, latency)

# Timer callback: hard IRQ which sets a flag to be tested by a priority coro,
# set each flag in turn
nflag = 0
def trig(t):
    global nflag
    flags[nflag].set_()
    nflag += 1
    nflag %= n_hp_tasks

tim = pyb.Timer(4)


# Have a number of normal tasks each using some CPU time
async def normal_task(delay):
    while True:
        time.sleep_ms(delay)  # Simulate processing
        await asyncio.sleep_ms(0)

# Measure the scheduling latency of a normal task which waits on an event.
# In this instance the driver returns immediately emulating an event which has
# already occurred - so we measure the scheduling latency.
async def norm_latency():
    global tmax, tmin
    device = DummyDeviceDriver()
    while True:
        await asyncio.sleep_ms(100)
        gc.collect()  # For precise timing
        tstart = time.ticks_us()
        await device  # Measure the latency
        delta = time.ticks_diff(time.ticks_us(), tstart)
        tmax = max(tmax, delta)
        tmin = min(tmin, delta)

# Ensure coros are running before we start the timer and measurement.
async def report():
    await asyncio.sleep_ms(100)
    tim.init(freq=10)
    tim.callback(trig)
    await asyncio.sleep(2)
    print('Max latency of urgent tasks: {}us'.format(max_latency))
    print('Latency of normal tasks: {:6.2f}ms max {:6.2f}ms min.'.format(tmax / 1000, tmin / 1000))
    tim.deinit()

print('Test runs for two seconds.')
loop = asyncio.get_event_loop(hpqlen = n_hp_tasks)
#loop.allocate_hpq(n_hp_tasks)  # Allocate a (small) high priority queue
loop.create_task(norm_latency())  # Measure latency of a normal task
for _ in range(n_tasks):
    loop.create_task(normal_task(1))  # Hog CPU for 1ms
for n in range(n_hp_tasks):
    loop.create_task(urgent(n))
loop.run_until_complete(report())
