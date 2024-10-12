# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import asyncio
import json
from machine import Pin

from mpy_blox.mqtt.hass.disco import MQTTMutableDiscoverable


class MQTTSwitch(MQTTMutableDiscoverable):
    component_type = 'switch'

    def __init__(self, name, pin_id, mqtt_connection,
                 discovery_prefix = 'homeassistant'):
        super().__init__(name,
                         mqtt_connection,
                         discovery_prefix=discovery_prefix)
        self.pin = Pin(pin_id, Pin.OUT)

    @property
    def app_disco_config(self):
        return {}

    @property
    def app_state(self):
        return 'ON' if self.pin.value() else 'OFF'

    async def handle_msg(self, msg):
        self.pin.value(msg.payload == b'ON')
        asyncio.create_task(self.publish_state())

    async def register(self):
        await super().register()
        await self.publish_state()
