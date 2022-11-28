# Interfacing uasyncio to interrupts

This note aims to provide guidance in resolving common queries about the use of
interrupts in `uasyncio` applications.

# 1. Does the requirement warrant an interrupt?

Writing an interrupt service routine (ISR) requires care: see the 
[official docs](https://docs.micropython.org/en/latest/reference/isr_rules.html).
There are restrictions (detailed below) on the way an ISR can interface with
`uasyncio`. Finally, on many platforms interrupts are a limited resource. In
short interrupts are extremely useful but, if a practical alternative exists,
it should be seriously considered.

Requirements that warrant an interrupt along with a `uasyncio` interface are
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
            await uasyncio.sleep_ms(0)
        data = device.read()
        # process the data
```
The overhead of polling is typically low. The MicroPython VM might use
300μs to determine that the device is not ready. This will occur once per
iteration of the scheduler, during which time every other pending task gets a
slice of execution. If there were five tasks, each of which used 5ms of VM time,
the overhead would be `0.3*100/(5*5)=1.2%` - see [latency](./INTERRUPTS.md#31-latency-in-uasyncio).

Devices such as pushbuttons and switches are best polled as, in most
applications, latency of (say) 100ms is barely detectable. Interrupts lead to
difficulties with
[contact bounce](http://www.ganssle.com/debouncing.htm) which is readily
handled using a simple [uasyncio driver](./DRIVERS.md). There may be exceptions
which warrant an interrupt such as fast games or cases where switches are
machine-operated such as limit switches.

## 2.2 The I/O mechanism

Devices such as UARTs and sockets are supported by the `uasyncio` stream
mechanism. The UART driver uses interrupts at a firmware level, but exposes
its interface to `uasyncio` by means of the `StreamReader` and `StreamWriter`
classes. These greatly simplify the use of such devices.

It is also possible to write device drivers in Python enabling the use of the
stream mechanism. This is covered in
[the tutorial](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#64-writing-streaming-device-drivers).

# 3. Using interrupts

This section details some of the issues to consider where interrupts are to be
used with `uasyncio`.

## 3.1 Latency in uasyncio

Consider an application with four continuously running tasks, plus a fifth
which is paused waiting on an interrupt. Each of the four tasks will yield to
the scheduler at intervals. Each task will have a worst-case period
of blocking between yields. Assume that the worst-case times for each task are
50, 30, 25 and 10ms. If the program logic allows it, the situation may arise
where all of these tasks are queued for execution, and all are poised to block
for the maximum period. Assume that at that moment the fifth task is triggered.

With current `uasyncio` design that fifth task will be queued for execution
after the four pending tasks. It will therefore run after  
(50+30+25+10) = 115ms  
An enhancement to `uasyncio` has been discussed that would reduce that to 50ms,
but that is the irreduceable minimum for any cooperative scheduler.

The key issue with latency is the case where a second interrupt occurs while
the first is still waiting for its `uasyncio` handler to be scheduled. If this
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
with ISR context because restictions remain on the use of `uasyncio`
operations. This is because such code can pre-empt the `uasyncio` scheduler.
This is discussed further below.

A solution to the encoder problem is to have the ISR maintain a value of the
encoder's position, with a `uasyncio` task polling this and triggering the GUI
callback. This ensures that the callback runs in a `uasyncio` context and can
run any Python code, including `uasyncio` operations such as creating and
cancelling tasks. This will work if the position value is stored in a single
word, because changes to a word are atomic (non-interruptible). A more general
solution is to use `uasyncio.ThreadSafeFlag`.

## 3.3 Interfacing an ISR with uasyncio

This should be read in conjunction with the discussion of the `ThreadSafeFlag`
in [the official docs](https://docs.micropython.org/en/latest/library/uasyncio.html#class-threadsafeflag)
and [the tutorial](./TUTORIAL.md#36-threadsafeflag).

Assume a hardware device capable of raising an interrupt when data is
available. The requirement is to read the device fast and subsequently process
the data using a `uasyncio` task. An obvious (but wrong) approach is:

```python
data = bytearray(4)
# isr runs in response to an interrupt from device
def isr():
    device.read_into(data)  # Perform a non-allocating read
    uasyncio.create_task(process_data())  # BUG
```

This is incorrect because when an ISR runs, it can pre-empt the `uasyncio`
scheduler with the result that `uasyncio.create_task()` may disrupt the
scheduler. This applies whether the interrupt is hard or soft and also applies
if the ISR has passed execution to another function via `micropython.schedule`:
as described above, all such code runs in an ISR context.

The safe way to interface between ISR-context code and `uasyncio` is to have a
coroutine with synchronisation performed by `uasyncio.ThreadSafeFlag`. The
following fragment illustrates the creation of a task in response to an
interrupt:
```python
tsf = uasyncio.ThreadSafeFlag()
data = bytearray(4)

def isr(_):  # Interrupt handler
    device.read_into(data)  # Perform a non-allocating read
    tsf.set()  # Trigger task creation

async def check_for_interrupts():
    while True:
        await tsf.wait()
        uasyncio.create_task(process_data())
```
It is worth considering whether there is any point in creating a task rather
than using this template:
```python
tsf = uasyncio.ThreadSafeFlag()
data = bytearray(4)

def isr(_):  # Interrupt handler
    device.read_into(data)  # Perform a non-allocating read
    tsf.set()  # Trigger task creation

async def process_data():
    while True:
        await tsf.wait()
        # Process the data here before waiting for the next interrupt
```

## 3.4 Thread Safe Classes

Other classes capable of being used to interface an ISR with `uasyncio` are
discussed [here](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/THREADING.md),
notably the `ThreadSafeQueue`.

# 4. Conclusion

The key take-away is that `ThreadSafeFlag` is the only official `uasyncio`
construct which can safely be used in an ISR context. Unofficial "thread
safe" classes may also be used.

###### [Main tutorial](./TUTORIAL.md#contents)
