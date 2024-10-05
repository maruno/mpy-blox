# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from gc import mem_free, mem_alloc
from os import remove, stat, statvfs

from mpy_blox.contextlib import suppress


def rewrite_file(file_path: str, new_content: bytes):
    # Temporary till truncate supported: https://github.com/micropython/micropython/issues/4775
    with suppress(OSError):
        if stat(file_path)[6] > len(new_content):
            remove(file_path)

    with open(file_path, 'wb') as f:
        f.write(new_content)


def log_vfs_state(path: str):
    f_bsize, _,f_blocks, f_bfree  = statvfs(path)[:4]
    total_kb = (f_blocks * f_bsize) / 1000
    free_kb = (f_bfree * f_bsize) / 1000
    used_kb =  total_kb - free_kb

    logging.info("VFS state %s: %s/%s, free %s (kB), blocksize %s",
                 path, used_kb, total_kb, free_kb, f_bsize)


def log_mem_state():
    free_kb = mem_free() / 1000
    used_kb = mem_alloc() / 1000
    total_kb = free_kb + used_kb
    logging.info("Memory heap state: %s/%s, free %s (kB)",
                 used_kb, total_kb, free_kb)
