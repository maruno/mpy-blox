# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import network
from utime import sleep


def connect_wlan(config):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(dhcp_hostname=config.get('hostname', 'espressif'))

    try:
        secure_cfg = config['secure']
        wlan.connect(secure_cfg['wlan.ssid'], secure_cfg['wlan.psk'])
    except KeyError:
        logging.warning("Network credentials not found. Device provisioned? "
                        "Can't boot with network support")
        return

    while not wlan.isconnected():
        logging.info('Waiting for WLAN connection...')
        sleep(1.0)
    
    sleep(1.0)  # Seems to be needed to ensure connectivity...
    logging.info('WLAN connected!')
