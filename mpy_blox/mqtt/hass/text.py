# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from mpy_blox.mqtt.hass.disco import MQTTDiscoverableState


class MQTTText(MQTTDiscoverableState):
    is_mutable = True
    component_type = 'text'
    
    def __init__(self,
                 name,
                 set_cb,
                 mqtt_connection,
                 discovery_prefix='homeassistant'):
        super().__init__(name, mqtt_connection,
                         discovery_prefix=discovery_prefix)
        self.set_cb = set_cb
        self.state = ''

    @property
    def app_state(self):
        return self.state

    async def handle_msg(self, msg):
        self.state = state = str(msg.payload, 'utf8')
        self.set_cb(state)
        await self.publish_state()
