# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from logging import getLogger


logger = getLogger('system')


async def blox_log_config(settings, network_available):
    replay_buffer = None
    if settings.get('logging.replay_buffer', False):
        from mpy_blox.log_handlers.replay_buffer import init_replay_buffer
        try:
            replay_buffer = init_replay_buffer(settings)
        except Exception as e:
            logger.warning("Failed to initialise replay_buffer", exc_info=e)

    # Network reliant log handlers
    if network_available:
        # Rudimentary syslog facility
        if 'logging.syslog.hostname' in settings:
            from mpy_blox.log_handlers.syslog import init_syslog
            try:
                logger.info("Trying to initialise syslog")
                init_syslog(settings)
            except Exception as e:
                logger.warning("Failed to initialise syslog", exc_info=e)

        # VT100 remote terminal
        if 'logging.remote_terminal.listen_host' in settings:
            from mpy_blox.log_handlers.remote_terminal import init_remote_terminal
            try:
                logger.info("Trying to initialise remote terminal")
                await init_remote_terminal(settings, replay_buffer)
            except Exception as e:
                logger.warning("Failed to initialise remote terminal",
                               exc_info=e)
