# rp2_touch.py
import rp2
from machine import Pin, Timer
import asyncio
from . import Pushbutton

# Array size 16 samples at 500Hz default = 32ms
_NSAMPLES = const(16)


@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, out_init=rp2.PIO.OUT_LOW, autopush=True, autopull=True)
def get_cap():
    out(y, 32)  # Wait for count from Python
    wrap_target()
    set(pindirs, 1)  # Set sense pin to output.
    set(pins, 1)[31]  # Drive it high and charge.
    in_(x, 30)  # Push count << 2 to Python. FIFO fills and SM stalls until a word is read.
    label("invalid")  # Discard overflow caused by excessive capacitance
    mov(x, y)  # Reset count
    set(pindirs, 0)  # Change to input
    label("loop")  # Wait for it to drift low
    jmp(x_dec, "next")
    jmp("invalid")  # x was 0 (now -1): discard invalid reading
    label("next")  # x was nonzero
    jmp(pin, "loop")  # Loop until sense pin reads low
    wrap()


def indx(i=0):  # Yield index values modulo _NSAMPLES
    while True:
        # yield (i := i - 1 if i else _NSAMPLES - 1)
        yield (i := (i + 1) & 0x0F)


class RP2Touch(Pushbutton):
    _sm_no = 0
    _freq = 500
    _thresh = 5

    @classmethod
    def config(cls, thresh=5, start_sm=0, freq=500):
        cls._sm_no = start_sm
        cls._freq = freq
        cls._thresh = thresh

    def __init__(self, pin_sense, suppress=False):
        self._a = bytearray(_NSAMPLES)
        self._idx = indx()
        self._offs = 0
        self._running = False  # Hold off until initialised

        self._sm = rp2.StateMachine(
            RP2Touch._sm_no,
            get_cap,
            freq=125_000_000,
            set_base=pin_sense,  # set pin mapping
            out_base=pin_sense,  # Pindirs mapping
            jmp_pin=pin_sense,
            in_shiftdir=rp2.PIO.SHIFT_RIGHT,
            push_thresh=30,
        )
        RP2Touch._sm_no += 1
        self._sm.active(1)
        self._sm.put(0xFF)  # Initialise SM with counter value
        super().__init__(pin_sense, suppress, False)

        # Timer runs continuously, populating the buffer with samples. If multiple
        # instances exist their timers will be out of phase by an arbitrary angle.
        self._tim = Timer(freq=RP2Touch._freq, mode=Timer.PERIODIC, callback=self._tcb, hard=True)
        asyncio.create_task(self._init())

    # Store an integer proportional to capacitance. Note right shift by 2: this
    # ensures a small int is returned, enabling use in a hard ISR.
    def _tcb(self, _):  # Timer callback: get a sample and put in buffer
        self._a[next(self._idx)] = 0xFF - self._sm.get(None, 2)

    def _init(self):  # Measure stray capacitance. Button must not be pressed
        await asyncio.sleep_ms(200)
        self._offs = sum(self._a) >> 4
        self._running = True

    # ***** Pushbutton override *****
    # Moving average of _NSAMPLES
    def rawstate(self):
        return self._running and (((sum(self._a) >> 4) - self._offs) > RP2Touch._thresh)

    def deinit(self):
        self._tim.deinit()
        self._sm.active(0)
        super().deinit()

    def value(self):  # User test function to help detemine threshold
        return self._offs, (sum(self._a) >> 4) - self._offs
