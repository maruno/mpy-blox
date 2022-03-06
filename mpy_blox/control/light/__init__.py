# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


class BasicLightControl:
    @property
    def power_state(self):
        raise NotImplementedError

    @power_state.setter
    def power_state_set(self, new_state):
        raise NotImplementedError
