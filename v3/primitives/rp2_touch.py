# rp2_touch.py RP2 hosts: support Pushbutton based on touch pad.

# Copyright (c) 2026 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Version optimised to minimise timer callback time for multiple buttons.

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
    label("full_scale")
    set(pindirs, 1)  # Set sense pin to output.
    set(pins, 1)[31]  # Drive it high and charge.
    in_(x, 30)  # Push count << 2 to Python. FIFO fills and SM stalls until a word is read.
    mov(x, y)  # Reset count
    set(pindirs, 0)  # Change to input
    label("loop")  # Wait for it to drift low
    jmp(x_dec, "next")  # Jump unless it's timed out
    set(x, 0)  # Return 0 on timeout (maximum time)
    jmp("full_scale")
    label("next")  # x was nonzero
    jmp(pin, "loop")  # Loop until sense pin reads low
    wrap()


class RP2Touch(Pushbutton):
    _sm_no = 0  # Initial state machine no.
    _freq = 500  # Poll frequency (Hz)
    _thresh = 5  # Detection threshold
    _insts = set()  # Instance list
    _idx = 0  # Index for above
    _tim = None  # Single Timer instance

    @classmethod
    def config(cls, thresh=5, start_sm=0, freq=500):  # Override defaults
        cls._sm_no = start_sm
        cls._freq = freq
        cls._thresh = thresh

    def __init__(self, pin_sense, suppress=False):
        self._a = bytearray(_NSAMPLES)
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
        super().__init__(pin_sense, suppress, False)  # No sense
        if RP2Touch._tim is None:  # Single timer instance. Callback gets a sample from the
            f = RP2Touch._freq  # SM and puts in the buffer for every class instance.
            RP2Touch._tim = Timer(freq=f, mode=Timer.PERIODIC, callback=self._tcb, hard=True)
        RP2Touch._insts.add(self)
        asyncio.create_task(self._init())

    # Timer callback: ~170μs with five buttons at stock 125MHz = 8.5% utilisation.
    # Store an integer from the SM. Note right shift by 2: this ensures a small int is
    # returned, enabling use in a hard ISR.
    @micropython.viper
    def _tcb(self, _):
        i: uint = uint(RP2Touch._idx)
        for inst in RP2Touch._insts:  # For each instance
            inst._a[i] = inst._sm.get(None, 2)  # Save a sample in buffer
        RP2Touch._idx = (i + 1) & 0x0F  # Update index modulo 16

    async def _init(self):  # Measure stray capacitance. Button must not be pressed
        await asyncio.sleep_ms(200)  # Ensure samples have baan gathered.
        self._offs = self._cap()
        self._running = True

    # Current capacitance value. Readings from the SM are summed then divided by
    # the number of samples to give mean. Capacitance is 0xFF - mean SM reading.
    # Optionally adjust for stray capacitance (offs).
    def _cap(self, offs=0):
        return 0xFF - (sum(self._a) >> 4) - offs

    def value(self):  # User test function to help detemine threshold
        return self._offs, self._cap(self._offs)

    # ***** Pushbutton class override *****
    # Moving average of _NSAMPLES
    def rawstate(self):
        return self._running and (self._cap(self._offs) > RP2Touch._thresh)

    def deinit(self):
        if (t := RP2Touch._tim) is not None:
            t.deinit()
            RP2Touch._tim = None
        self._sm.active(0)
        super().deinit()
