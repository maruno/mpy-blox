# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from os import remove, stat

from mpy_blox.contextlib import suppress


def rewrite_file(file_path: str, new_content: bytes):
    # Temporary till truncate supported: https://github.com/micropython/micropython/issues/4775
    with suppress(OSError):
        if stat(file_path)[6] > len(new_content):
            remove(file_path)

    with open(file_path, 'wb') as f:
        f.write(new_content)
