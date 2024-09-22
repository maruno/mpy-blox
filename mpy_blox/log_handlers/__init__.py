# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


def blox_log_config(settings, network_available):
    if network_available:
        # Network reliant log handlers
        if 'logging.syslog.hostname' in settings:
            from mpy_blox.log_handlers.syslog import init_syslog
            init_syslog(settings)
