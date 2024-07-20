# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from mpy_blox.display.iv17.charset import charset_ndp


def create_framebuffer(message):
    characters_len = len(list(filter(lambda s: s != '.', message)))
    padding = (4 - characters_len % 4) % 4
    if padding:
        # Pad with spaces so we use a full board
        message += ' ' * padding

    dots_len = characters_len // 4 + 1
    framebuffer = bytearray((0,) * (characters_len * 2 + dots_len))

    current_dot = 0
    fbuff_idx = -2
    char_idx = -1
    for value in message:
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
