# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import micropython

import asyncio
import gc
from esp import osdebug
from logging import getLogger
from machine import reset
from sys import print_exception
from uio import StringIO

from mpy_blox.config import init_config
from mpy_blox.log_handlers import blox_log_config
from mpy_blox.log_handlers.formatter import VTSGRColorFormatter
from mpy_blox.mqtt import MQTTConnectionManager
from mpy_blox.mqtt.update import MQTTUpdateChannel
from mpy_blox.network import connect_wlan
from mpy_blox.time import sync_ntp, scheduled_sync_task
from mpy_blox.util import log_vfs_state, log_mem_state


logger = getLogger('system')


def asyncio_exception_handler(loop, context):
    fut = context['future']
    logger.warning("%s, future: %s coro=%s",
                   context['message'],fut, fut.coro,
                   exc_info=context['exception'])


def start_network(config):
    if config.get('network.disabled', False):
        logger.info("Networking disabled")
        return False

    connect_wlan(config)
    sync_ntp(config)
    asyncio.create_task(scheduled_sync_task(config))

    return True


async def register_updates(config, mqtt_connection):
    channel = config.get('update.channel')
    if not channel:
        logger.info("MPy-BLOX: No update channel configured")
        return

    auto_update = config.get('update.auto_update')
    update_channel = MQTTUpdateChannel(channel,
                                       auto_update,
                                       mqtt_connection)
    await update_channel.register()
    if auto_update:
        logger.info("MPy-BLOX: Waiting for possible auto update...")
        await update_channel.update_done.wait()

        if update_channel.pkgs_installed:
            logger.info(
                "MPy-BLOX: Update on boot succesful, rebooting with new code")
            reset()


def main():
    config = init_config()

    emergency_buf_len = int(config.get('emergency_buf_len', 100))
    if emergency_buf_len:
        logger.info("Allocating %s emergency buffer", emergency_buf_len)
        micropython.alloc_emergency_exception_buf(emergency_buf_len)

    # Register our own asyncio exception handler using logging
    asyncio.get_event_loop().set_exception_handler(asyncio_exception_handler)

    # Enable VT mode on serial terminal now
    getLogger().handlers[0].setFormatter(VTSGRColorFormatter())

    network_available = start_network(config)
    asyncio.run(blox_log_config(config, network_available))

    # We are booted, no more need for kernel messages
    osdebug(None)

    # Run GC from initial boot
    gc.collect()

    logger.info('Mpy-BLOX: Core succesfully booted')
    log_vfs_state('/')
    log_mem_state()

    if network_available:
        logger.info("MPy-BLOX: Network available, connecting MQTT")
        mqtt_conn= MQTTConnectionManager.get_connection()
        asyncio.run(mqtt_conn.connect())
        asyncio.run(register_updates(config, mqtt_conn))

    # Run GC after starting MQTT
    gc.collect()

    try:
        from user_main import user_main
        asyncio.run(user_main())
    except ImportError as e:
        logger.info("Missing user_main, going to REPL")
        print_exception(e)


def main_except_reset():
    try:
        main()
    except Exception as e:
        logger.critical(
            "Master exception handler, rebooting...\n")

        exception_info_io = StringIO()
        print_exception(e, exception_info_io)
        logger.critical(
            "%s: %s, Exception info follows\n\n%s",
            e.__class__.__name__, e,
            exception_info_io.getvalue())

        reset()


if __name__ == '__main__':
    main()
