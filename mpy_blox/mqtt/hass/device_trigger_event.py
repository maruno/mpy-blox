# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from logging import getLogger

from mpy_blox.mqtt.hass.disco import MQTTDiscoverable
from mpy_blox.mqtt.protocol.message import MQTTMessage


logger = getLogger('mqtt_hass')


class MQTTDeviceTriggerEvent(MQTTDiscoverable):
    component_type = 'device_automation'

    def __init__(self, name, type, subtype, mqtt_connection,
                 device_index=None, discovery_prefix='homeassistant'):
        super().__init__(name, mqtt_connection, device_index, discovery_prefix)
        self._type = type
        self._subtype = subtype

    @property
    def app_disco_config(self):
        return {
            'topic': '~/events',
            'automation_type': 'trigger',
            'type': self._type,
            'subtype': self._subtype,
            'payload': self.payload_ident
        }

    @property
    def payload_ident(self):
        return '{}/{}'.format(self._type, self._subtype)

    async def fire(self):
        payload_ident = self.payload_ident
        logger.info("Sending MQTT device trigger event %s", payload_ident)
        await self.mqtt_conn.publish(
            MQTTMessage(
                '{}/events'.format(self.topic_prefix),
                payload_ident
            )
        )
