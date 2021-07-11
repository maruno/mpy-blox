# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uasyncio as asyncio
import logging
from esp import osdebug
from machine import reset
from sys import print_exception
from uio import StringIO

from mpy_blox.config import init_config
from mpy_blox.network import connect_wlan
from mpy_blox.syslog import init_syslog
from mpy_blox.time import sync_ntp


def main():
    config = init_config()
    logging.debug("Read config %s", config)
    
    connect_wlan(config)
    sync_ntp(config)
    init_syslog(config)
    
    # We are booted, no more need for kernel messages
    osdebug(None)
    logging.info('Mpy-BLOX succesfully booted')
    
    from user_main import user_main
    asyncio.run(user_main())


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.critical(
            "Master exception handler, rebooting...\n")

        exception_info_io = StringIO()
        print_exception(e, exception_info_io)
        logging.critical(
            "%s: %s, Exception info follows\n\n%s",
            e.__class__.__name__, e,
            exception_info_io.getvalue())

        reset()
