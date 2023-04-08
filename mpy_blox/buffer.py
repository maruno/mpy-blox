# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import micropython

class PreAllocatedRingBuffer:
    def __init__(self, size, length):
        self.length = length
        self.head = self.tail = 0
        self.data = tuple([bytearray(size) for _ in range(0, length)])

    @micropython.viper
    def full(self) -> bool:
        return (int(self.head) + 1) % int(self.length) == int(self.tail)

    def empty(self):
        return self.head == self.tail

    def head_ptr(self):
        return self.data[self.head]

    @micropython.viper
    def _calculate_new_head(self) -> int:
        return (int(self.head) + 1) % int(self.length)

    def advance_head(self):
        self.head = self._calculate_new_head()

    def iter_read(self):
        idx = self.tail
        length = self.length
        while idx != self.head:  # while not empty
            self.tail = new_idx = (idx + 1) % length
            yield memoryview(self.data[idx])

            idx = new_idx
