# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging


async def blox_log_config(settings, network_available):
    if network_available:
        # Network reliant log handlers
        if 'logging.syslog.hostname' in settings:
            from mpy_blox.log_handlers.syslog import init_syslog
            try:
                init_syslog(settings)
            except Exception:
                logging.warning("Failed to initialise syslog")
        if 'logging.remote_terminal.listen_host' in settings:
            from mpy_blox.log_handlers.remote_terminal import init_remote_terminal
            try:
                await init_remote_terminal(settings)
            except Exception:
                logging.warning("Failed to initialise remote terminal")
