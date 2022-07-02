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
from mpy_blox.mqtt.update import MQTTUpdateChannel
from mpy_blox.network import connect_wlan
from mpy_blox.syslog import init_syslog
from mpy_blox.time import sync_ntp


def start_network(config):
    if config.get('network.disabled', False):
        logging.info("Networking disabled")
        return False

    connect_wlan(config)
    sync_ntp(config)
    init_syslog(config)

    return True


async def register_updates(config):
    channel = config.get('update.channel')
    if not channel:
        logging.info("No update channel configured")
        return

    auto_update = config.get('update.auto_update')
    update_channel = MQTTUpdateChannel(channel, auto_update)
    await update_channel.connect()
    if auto_update:
        logging.info("Waiting for possible auto update...")
        await update_channel.update_done.wait()


def main():
    config = init_config()
    
    network_available = start_network(config)
    
    # We are booted, no more need for kernel messages
    osdebug(None)
    logging.info('Mpy-BLOX: Core succesfully booted')
    
    if network_available:
        asyncio.run(register_updates(config))

    try:
        from user_main import user_main
        asyncio.run(user_main())
    except ImportError as e:
        logging.info("Missing user_main, going to REPL")
        print_exception(e)


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
