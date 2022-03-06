# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import uasyncio as asyncio
import ujson

from mpy_blox.mqtt.hass.disco import MQTTMutableDiscoverable
from mpy_blox.control.light.pin_based import PinBasedLightControl


class MQTTLight(MQTTMutableDiscoverable):
    component_type = 'light'

    def __init__(self, name, light_control, discovery_prefix = 'homeassistant'):
        super().__init__(name,
                         msg_cb=self.msg_rcvd,
                         discovery_prefix=discovery_prefix)
        self.light_control = light_control

    @property
    def app_disco_config(self):
        return {'brightness': False, 'schema': 'json'}
    
    @property
    def app_state(self):
        return {
            'state': 'ON' if self.light_control.power_state else 'OFF'
        }

    def msg_rcvd(self, topic, msg, retained):
        msg = ujson.loads(msg)
        logging.info('Received message for %s: %s', topic.decode(), msg)

        if 'state' in msg:
            self.light_control.power_state = msg['state'] == 'ON'
            asyncio.create_task(self.publish_state())
    
    async def listen(self):
        await self.mqtt_client.subscribe('{}/set'.format(self.topic_prefix))
    
    async def connect(self):
        await super().connect()
        await self.publish_state()
        await self.listen()


async def async_main():
    # Setup closet lights on GPIO 4
    mqtt_light = MQTTLight('Closet lights', PinBasedLightControl(4))
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
