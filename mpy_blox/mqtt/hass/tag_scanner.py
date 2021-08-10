# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import ujson


from mpy_blox.mqtt.hass.disco import MQTTDiscoverable


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
        await self.mqtt_client.publish(
            '{}/scanned'.format(self.topic_prefix),
            ujson.dumps({
                'tag_id': str(tag_id)
            }),
            qos=1
        )


async def user_main():
    from uasyncio import sleep
    """Demo app for MQTT scanner."""
    mqtt_tag_scanner = MQTTTagScanner("Demo MQTT scanner",
                                      device_index='demo')
    await mqtt_tag_scanner.connect()
    
    await sleep(1)
    await mqtt_tag_scanner.tag_scanned('TEST TAG')
