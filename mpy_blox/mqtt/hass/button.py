# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from mpy_blox.mqtt.hass.disco import MQTTDiscoverable


class MQTTButton(MQTTDiscoverable):
    is_mutable = True
    
    def __init__(self,
                 name,
                 press_cb,
                 device_index=None,
                 discovery_prefix='homeassistant'):
        super().__init__(name, self.msg_rcvd, device_index, discovery_prefix)
        self.press_cb = press_cb
    
    @property
    def app_disco_config(self):
        return {
            'entity_category': 'config'
        }

    def msg_rcvd(self, topic, msg, retained):
        logging.info('Received message for %s: %s', topic.decode(), msg)
        if msg == b'PRESS':
            self.press_cb()
