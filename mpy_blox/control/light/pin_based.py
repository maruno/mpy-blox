# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from machine import Pin

from mpy_blox.control.light import BasicLightControl


class PinBasedLightControl:
    def __init__(self, pin_id):
        self.pin = Pin(pin_id, Pin.OUT)

    @property
    def power_state(self):
        return self.pin.value()


    @power_state.setter
    def power_state_set(self, new_state):
        self.pin.value(new_state)