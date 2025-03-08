# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# This whole module assumes  an arrangement of 8 chips for 4 displays
# with 1 extra dot chip taking care of all 8 dots for those displays.

from micropython import const

import asyncio
from collections import deque
from logging import getLogger
from time import time
from mpy_blox.display.iv17.charset import charset_ndp


logger = getLogger('IV17')

MAX_MSGS_WAITING = const(10)


def create_framebuffer(msg):
    characters_len = len(list(filter(lambda s: s != '.', msg)))
    padding = (4 - characters_len % 4) % 4
    if padding:
        # Pad with spaces so we use a full board
        msg += ' ' * padding
        characters_len += padding

    dots_len = characters_len // 4 + 1
    framebuffer = bytearray((0,) * (characters_len * 2 + dots_len))

    current_dot = 0
    fbuff_idx = -2
    char_idx = -1
    for value in msg:
        if value == '.':
            # Append dot information to previous character
            current_dot ^= 0b10 << char_idx % 4 * 2
        else:
            # Write out a full character
            value = value.upper()
            char_idx -= 1

            # Get character fragments and add to framebuffer
            fragment_1, fragment_2 = charset_ndp[value]
            framebuffer[fbuff_idx] = fragment_2
            fbuff_idx -= 1
            framebuffer[fbuff_idx] = fragment_1
            fbuff_idx -= 1

        if fbuff_idx % 10 == 0:
            # Set current dot and reset
            framebuffer[fbuff_idx + 9] = current_dot
            current_dot = 0
            fbuff_idx -= 1  # Skip the new dot driver, set later

    return framebuffer


class IV17Display:
    def __init__(self, shift_register, chain_len, scroll_rate=0.5):
        self.shift_register = shift_register
        self.chain_len = chain_len
        self.scroll_rate = scroll_rate

        # Task helpers
        self.msg_display_task = None

        # Queued display message storage
        self.msg_available = asyncio.Event()
        self.msg_deque = deque((), MAX_MSGS_WAITING)

    async def __aenter__(self):
        self.start()
        return self

    def start(self):
        self.msg_display_task = asyncio.create_task(self._msg_display_loop())
        self.clear()

    def queue_message(self, msg, timeout):
        self.msg_deque.appendleft((msg, timeout))
        self.msg_available.set()

    async def _msg_display_loop(self):
        event = self.msg_available
        msg_deque = self.msg_deque
        display_text = self.display_text
        while True:
            await event.wait()
            msg, timeout = msg_deque.pop()
            if not msg_deque:
                event.clear()

            await display_text(msg, timeout)

    def clear(self):
        chain_len = self.chain_len
        dots_len = chain_len // 4 + 1
        self.shift_register.write(bytes((0,) * (chain_len * 2 + dots_len)))

    # TODO Should this one become private?
    def display_text(self, msg, timeout):
        # TODO Get lock?

        # First clear the current display
        self.clear()

        # Check if we need to scroll or can display statically
        msg_len = len(msg)
        if self.chain_len >= msg_len:
            return self._static_text(msg, timeout)
        else:
            return self._scroll_text(msg, timeout)

    async def _static_text(self, msg, timeout):
        logger.info("Displaying static text '%s' for %s seconds", msg, timeout)

        self.shift_register.write(create_framebuffer(msg))
        await asyncio.sleep(timeout)

    async def _scroll_text(self, msg, timeout):
        logger.info("Displaying scrolling text '%s' for %s seconds",
                    msg, timeout)

        shift_nr = 0
        direction = 1
        msg_len = len(msg)
        start_time = time()
        chain_len = self.chain_len
        scroll_rate = self.scroll_rate
        shift_register = self.shift_register
        while time() - start_time < timeout:
            shifted_msg = msg[shift_nr:shift_nr+4]
            logger.info("Displaying shift: %s", shifted_msg)
            # TODO Maybe the framebuffers could be cached
            shift_register.write(create_framebuffer(shifted_msg))

            await asyncio.sleep(scroll_rate)
            if ((msg_len - shift_nr - chain_len == 0)
                    or (direction == -1 and shift_nr == 0)):
                direction *= -1

            shift_nr += direction

    def stop(self):
        if self.msg_display_task:
            self.msg_display_task.cancel()

    async def __aexit__(self, exc_type, exc, tb):
        self.stop()

        return exc is None
