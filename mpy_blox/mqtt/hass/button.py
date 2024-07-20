# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from mpy_blox.mqtt.hass.disco import MQTTDiscoverable


class MQTTButton(MQTTDiscoverable):
    is_mutable = True
    component_type = 'button'
    
    def __init__(self,
                 name,
                 press_cb,
                 mqtt_connection,
                 discovery_prefix='homeassistant'):
        super().__init__(name, mqtt_connection,
                         discovery_prefix=discovery_prefix)
        self.press_cb = press_cb

    @property
    def app_disco_config(self):
        return {
            'entity_category': 'config'
        }

    async def handle_msg(self, msg):
        if msg.payload == b'PRESS':
            await self.press_cb()
