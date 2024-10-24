# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# This whole module assumes  an arrangement of 8 chips for 4 displays
# with 1 extra dot chip taking care of all 8 dots for those displays.

import asyncio
from logging import getLogger
from time import time
from mpy_blox.display.iv17.charset import charset_ndp


logger = getLogger('IV17')


async def scroll_text(msg, timeout, shift_register, chain_len,
                      scroll_rate=0.5):
    logger.info("Displaying scrolling text '%s' for %s seconds",
                msg, timeout)

    # Clear the shift register
    dots_len = chain_len // 4 + 1
    shift_register.write(bytes((0,) * (chain_len * 2 + dots_len)))

    # Check if we need to scroll at all
    # TODO: Move to class...
    msg_len = len(msg)
    if chain_len >= msg_len:
        logger.info("Displaying whole msg: %s", msg)
        shift_register.write(create_framebuffer(msg))
        await asyncio.sleep(timeout)
        return

    shift_nr = 0
    direction = 1
    start_time = time()
    while time() - start_time < timeout:
        shifted_msg = msg[shift_nr:shift_nr+4]
        logger.info("Displaying shift: %s", shifted_msg)
        shift_register.write(create_framebuffer(shifted_msg))

        await asyncio.sleep(scroll_rate)
        if ((msg_len - shift_nr - chain_len == 0)
                or (direction == -1 and shift_nr == 0)):
            direction *= -1

        shift_nr += direction


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
