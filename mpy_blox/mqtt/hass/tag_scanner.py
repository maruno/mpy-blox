# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from mpy_blox.mqtt.hass.disco import MQTTDiscoverable
from mpy_blox.mqtt.protocol.message import MQTTMessage


class MQTTTagScanner(MQTTDiscoverable):
    component_type = 'tag'
    include_top_level_device_cfg = False

    @property
    def app_disco_config(self):
        return {
            'topic': '~/scanned',
            'value_template': "{{ value_json.tag_id }}"
        }

    async def tag_scanned(self, tag_id):
        logging.info("Sending tag scanned event, tag ID %s", tag_id)
        await self.mqtt_conn.publish(
            MQTTMessage(
                '{}/scanned'.format(self.topic_prefix),
                {
                    'tag_id': str(tag_id)
                }
            )
        )
