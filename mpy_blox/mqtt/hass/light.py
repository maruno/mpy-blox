# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import uasyncio as asyncio
import ujson
from machine import Pin

from mpy_blox.mqtt.hass.disco import MQTTMutableDiscoverable


class MQTTLight(MQTTMutableDiscoverable):
    component_type = 'light'

    def __init__(self, name, pin_id, discovery_prefix = 'homeassistant'):
        super().__init__(name,
                         msg_cb=self.msg_rcvd,
                         discovery_prefix=discovery_prefix)
        self.pin = Pin(pin_id, Pin.OUT)

    @property
    def app_disco_config(self):
        return {'brightness': False, 'schema': 'json'}
    
    @property
    def app_state(self):
        return {
            'state': 'ON' if self.pin.value() else 'OFF'
        }

    def msg_rcvd(self, topic, msg, retained):
        msg = ujson.loads(msg)
        logging.info('Received message for %s: %s', topic.decode(), msg)

        if 'state' in msg:
            self.pin.value(msg['state'] == 'ON')
            asyncio.create_task(self.publish_state())
    
    async def listen(self):
        await self.mqtt_client.subscribe('{}/set'.format(self.topic_prefix))
    
    async def connect(self):
        await super().connect()
        await self.publish_state()
        await self.listen()


async def async_main():
    # Setup closet lights on pin D2 (GPIO 4)
    mqtt_light = MQTTLight('Closet lights', 4)
    print("Topic prefix: {}".format(mqtt_light.topic_prefix))

    loop = asyncio.get_event_loop()
    await mqtt_light.connect()
    loop.run_forever()


def main():
    """Demo app for MQTT device discovery."""
    # Initialize logging
    logging.basicConfig(format="{asctime} {message}", style="{")
    asyncio.run(async_main())


if __name__ == '__main__':
    main()
