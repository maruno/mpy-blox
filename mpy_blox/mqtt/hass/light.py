import logging
import ujson
from machine import Pin
from ubinascii import hexlify

from mpy_blox.mqtt.hass.disco import MQTTDiscoverable


class MQTTLight(MQTTDiscoverable):
    component_type = 'light'

    def __init__(self, name, pin_id, discovery_prefix = 'homeassistant'):
        super().__init__(discovery_prefix)
        self.name = name
        self.pin = Pin(pin_id, Pin.OUT)
        self.mqtt_client.set_callback(self.msg_rcvd)

    def publish_config(self):
        logging.info('Sending %s discoverability config',
                     self.__class__.__name__)
        self.mqtt_client.publish(
            '{}/config'.format(self.topic_prefix),
            ujson.dumps({
                '~': self.topic_prefix,
                'name': self.name,
                'unique_id': self.entity_id,
                'cmd_t': '~/set',
                'stat_t': '~/state',
                'schema': 'json',
                'brightness': False
            })
        )

    def publish_state(self):
        self.mqtt_client.publish(
            '{}/state'.format(self.topic_prefix),
            ujson.dumps({
                'state': 'ON' if self.pin.value() else 'OFF'
            })
        )
    
    def msg_rcvd(self, topic, msg):
        msg = ujson.loads(msg)
        logging.info('Received message for %s: %s', topic.decode(), msg)

        if 'state' in msg:
            self.pin.value(msg['state'] == 'ON')
            self.publish_state()
    
    def listen(self):
        self.mqtt_client.subscribe('{}/set'.format(self.topic_prefix))
        while True:
            self.mqtt_client.wait_msg()
    
    def connect(self):
        self.mqtt_client.connect()
        self.publish_config()
        self.publish_state()
        self.listen()


def main():
    """Demo app for MQTT device discovery."""
    # Initialize logging
    logging.basicConfig(format="{asctime} {message}", style="{")

    # Setup closet lights on pin D2 (GPIO 4)
    mqtt_light = MQTTLight('Closet lights', 4)
    print("Topic prefix: {}".format(mqtt_light.topic_prefix))

    mqtt_light.connect()


if __name__ == '__main__':
    main()