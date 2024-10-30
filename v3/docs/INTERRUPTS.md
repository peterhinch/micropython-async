# Interfacing asyncio to interrupts

This note aims to provide guidance in resolving common queries about the use of
interrupts in `asyncio` applications.

# 1. Does the requirement warrant an interrupt?

Writing an interrupt service routine (ISR) requires care: see the
[official docs](https://docs.micropython.org/en/latest/reference/isr_rules.html).
There are restrictions (detailed below) on the way an ISR can interface with
`asyncio`. Finally, on many platformasyncioupts are a limited resource. In
short interrupts are extremely useful but, if a practical alternative exists,
it should be seriously considered.

Requirements that warrant an interrupt along with a `asyncio` interface are
ones that require a microsecond-level response, followed by later processing.
Examples are:
 * Where the event requires an accurate timestamp.
 * Where a device supplies data and needs to be rapidly serviced. Data is put
 in a pre-allocated buffer for later processing.

Examples needing great care:
 * Where arrival of data triggers an interrupt and subsequent interrupts may
 occur after a short period of time.
 * Where arrival of an interrupt triggers complex application behaviour: see
 notes on [context](./INTERRUPTS.md#32-context).

# 2. Alternatives to interrupts

## 2.1 Polling

An alternative to interrupts is to use polling. For values that change slowly
such as ambient temperature or pressure this simplification is achieved with no
discernible impact on performance.
```python
temp = 0
async def read_temp():
    global temp
    while True:
        temp = thermometer.read()
        await asyncio.sleep(60)
```
In cases where interrupts arrive at a low frequency it is worth considering
whether there is any gain in using an interrupt rather than polling the
hardware:

```python
async def read_data():
    while True:
        while not device.ready():
            await asyncio.sleep_ms(0)
        data = device.read()
        # process the data
```
The overhead of polling is typically low. The MicroPython VM might use
300μs to determine that the device is not ready. This will occur once per
iteration of the scheduler, during which time every other pending task gets a
slice of execution. If there were five tasks, each of which used 5ms of VM time,
the overhead would be `0.3*100/(5*5)=1.2%` - see [latency](./INTERRUPTS.md#31-latency-in-asyncio).

Devices such as pushbuttons and switches are best polled as, in most
applications, latency of (say) 100ms is barely detectable. Interrupts lead to
difficulties with
[contact bounce](http://www.ganssle.com/debouncing.htm) which is readily
handled using a simple [asyncio driver](./DRIVERS.md). There may be exceptions
which warrant an interrupt such as fast games or cases where switches are
machine-operated such as limit switches.

## 2.2 The I/O mechanism

Devices such as UARTs and sockets are supported by the `asyncio` stream
mechanism. The UART driver uses interrupts at a firmware level, but exposes
its interface to `asyncio` by means of the `StreamReader` and `StreamWriter`
classes. These greatly simplify the use of such devices.

It is also possible to write device drivers in Python enabling the use of the
stream mechanism. This is covered in
[the tutorial](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#64-writing-streaming-device-drivers).

# 3. Using interrupts

This section details some of the issues to consider where interrupts are to be
used with `asyncio`.

## 3.1 Latency in asyncio

Consider an application with four continuously running tasks, plus a fifth
which is paused waiting on an interrupt. Each of the four tasks will yield to
the scheduler at intervals. Each task will have a worst-case period
of blocking between yields. Assume that the worst-case times for each task are
50, 30, 25 and 10ms. If the program logic allows it, the situation may arise
where all of these tasks are queued for execution, and all are poised to block
for the maximum period. Assume that at that moment the fifth task is triggered.

With current `asyncio` design that fifth task will be queued for execution
after the four pending tasks. It will therefore run after  
(50+30+25+10) = 115ms  
An enhancement to `asyncio` has been discussed that would reduce that to 50ms,
but that is the irreduceable minimum for any cooperative scheduler.

The key issue with latency is the case where a second interrupt occurs while
the first is still waiting for its `asyncio` handler to be scheduled. If this
is a possibility, mechanisms such as buffering or queueing must be considered.

## 3.2 Context

Consider an incremental encoder providing input to a GUI. Owing to the need to
track phase information an interrupt must be used for the encoder's two
signals. An ISR determines the current position of the encoder, and if it has
changed, calls a method in the GUI code.

The consequences of this can be complex. A widget's visual appearance may
change. User callbacks may be triggered, running arbitrary Python code.
Crucially all of this occurs in an ISR context. This is unacceptable for all
the reasons identified in
[this doc](https://docs.micropython.org/en/latest/reference/isr_rules.html).

Note that using `micropython.schedule` does not address every issue associated
with ISR context because restictions remain on the use of `asyncio`
operations. This is because such code can pre-empt the `asyncio` scheduler.
This is discussed further below.

A solution to the encoder problem is to have the ISR maintain a value of the
encoder's position, with a `asyncio` task polling this and triggering the GUI
callback. This ensures that the callback runs in a `asyncio` context and can
run any Python code, including `asyncio` operations such as creating and
cancelling tasks. This will work if the position value is stored in a single
word, because changes to a word are atomic (non-interruptible). A more general
solution is to use `asyncio.ThreadSafeFlag`.

## 3.3 Interfacing an ISR with asyncio

This should be read in conjunction with the discussion of the `ThreadSafeFlag`
in [the official docs](https://docs.micropython.org/en/latest/library/asyncio.html#asyncio.ThreadSafeFlag)
and [the tutorial](./TUTORIAL.md#36-threadsafeflag).

Assume a hardware device capable of raising an interrupt when data is
available. The requirement is to read the device fast and subsequently process
the data using a `asyncio` task. An obvious (but wrong) approach is:

```python
data = bytearray(4)
# isr runs in response to an interrupt from device
def isr():
    device.read_into(data)  # Perform a non-allocating read
    asyncio.create_task(process_data())  # BUG
```

This is incorrect because when an ISR runs, it can pre-empt the `asyncio`
scheduler with the result that `asyncio.create_task()` may disrupt the
scheduler. This applies whether the interrupt is hard or soft and also applies
if the ISR has passed execution to another function via `micropython.schedule`:
as described above, all such code runs in an ISR context.

The safe way to interface between ISR-context code and `asyncio` is to have a
coroutine with synchronisation performed by `asyncio.ThreadSafeFlag`. The
following fragment illustrates the creation of a task in response to an
interrupt:
```python
tsf = asyncio.ThreadSafeFlag()
data = bytearray(4)

def isr(_):  # Interrupt handler
    device.read_into(data)  # Perform a non-allocating read
    tsf.set()  # Trigger task creation

async def check_for_interrupts():
    while True:
        await tsf.wait()
        asyncio.create_task(process_data())
```
It is worth considering whether there is any point in creating a task rather
than using this template:
```python
tsf = asyncio.ThreadSafeFlag()
data = bytearray(4)

def isr(_):  # Interrupt handler
    device.read_into(data)  # Perform a non-allocating read
    tsf.set()  # Trigger task creation

async def process_data():
    while True:
        await tsf.wait()
        # Process the data here before waiting for the next interrupt
```
## 3.4 micropython.RingIO

This is a byte-oriented circular buffer [documented here]
(https://docs.micropython.org/en/latest/library/micropython.html#micropython.RingIO),
which provides an efficient way to return data from an ISR to an `asyncio` task.
It is implemented in C so performance is high, and supports stream I/O. The
following is a usage example:
```py
import asyncio
from machine import Timer
import micropython
micropython.alloc_emergency_exception_buf(100)

imu = SomeDevice()  # Fictional hardware IMU device

FRAMESIZE = 8  # Count, x, y, z accel
BUFSIZE = 200  # No. of records. Size allows for up to 200ms of asyncio latency.
rio = micropython.RingIO(FRAMESIZE * BUFSIZE + 1)  # RingIO requires an extra byte
count = 0x4000  # Bit14 is "Start of frame" marker. Low bits are a frame counter.

def cb(_):  # Timer callback. Runs at 1KHz.
    global count  # Frame count
    imu.get_accel_irq()  # Trigger the device
    rio.write(chr(count >> 8))
    rio.write(chr(count & 0xff))
    rio.write(imu.accel.ix)  # Device returns bytes objects (length 2)
    rio.write(imu.accel.iy)
    rio.write(imu.accel.iz)
    count += 1

async def main(nrecs):
    t = Timer(freq=1_000, callback=cb)
    sreader = asyncio.StreamReader(rio)
    rpb = 100  # Records per block
    blocksize = FRAMESIZE * rpb
    with open('/sd/imudata', 'wb') as f:
        swriter = asyncio.StreamWriter(f, {})
        while nrecs:
            data = await sreader.readexactly(blocksize)
            swriter.write(data)
            await swriter.drain()
            nrecs -= rpb
    t.deinit()

asyncio.run(main(1_000))
```
In this example data is acquired at a timer-controlled rate of 1KHz, with eight
bytes being written to the `RingIO` every tick. The `main()` task reads the data
stream and writes it out to a file. Similar code was tested on a Pyboard 1.1.

## 3.5 Other Thread Safe Classes

Other classes capable of being used to interface an ISR with `asyncio` are
discussed [here](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/THREADING.md),
notably the `ThreadSafeQueue`. This ring buffer allows entries to be objects
other than bytes. It supports the asynchronous iterator protocol (rather than
stream I/O) and is written in Python.

# 4. Conclusion

The `ThreadSafeFlag` and `RingIO` classes are the official `asyncio` constructs
which can safely be used in an ISR context. Unofficial "thread safe" classes may
also be used. Beware of classes such as `Queue` and `RingbufQueue` which are not
thread safe.

###### [Main tutorial](./TUTORIAL.md#contents)
