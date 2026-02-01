# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import asyncio
import gc
from logging import getLogger

from mpy_blox.config import init_config
from mpy_blox.util import log_vfs_state, log_mem_state

logger = getLogger('system')


def asyncio_exception_handler(loop, context):
    fut = context['future']
    logger.warning("%s, future: %s coro=%s",
                   context['message'],fut, fut.coro,
                   exc_info=context['exception'])


def main():
    init_config(unix_cwd=True)

    # Register our own asyncio exception handler using logging
    asyncio.get_event_loop().set_exception_handler(asyncio_exception_handler)

    # Run GC from initial boot
    gc.collect()

    log_vfs_state('/')
    log_mem_state()
    logger.info('Mpy-BLOX: Limited UNIX Core succesfully loaded')

    try:
        from user_main import user_main
        asyncio.run(user_main())
    except ImportError as e:
        logger.info("Missing user_main, exiting")
        from sys import exit
        exit(64)  # os.EX_USAGE


if __name__ == '__main__':
    main()
