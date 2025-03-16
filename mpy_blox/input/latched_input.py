# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from asyncio import ThreadSafeFlag
from machine import Pin

class LatchedInput:
    def __init__(self, pin_nr) -> None:
        self.pin  = Pin(pin_nr, Pin.IN)
        self.tsf = ThreadSafeFlag()
        self.reset()

    def isr(self, pin):
        pin.irq(handler=None)
        self.tsf.set()

    def reset(self):
        self.pin.irq(handler=self.isr, trigger=Pin.IRQ_RISING)

    def wait(self):
        return self.tsf.wait()
