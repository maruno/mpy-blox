import logging
import ujson
from uos import uname
from machine import Pin, unique_id
from ubinascii import hexlify

from umqtt.simple import MQTTClient


class MQTTDiscoverable:
    component_type = None
    def __init__(self, discovery_prefix = 'homeassistant'):
        self.discovery_prefix = discovery_prefix
        self.mqtt_client = MQTTClient(
            client_id=self.entity_id,
            server='172.16.3.1',
            user='homeassistant',
            password='hassamateurtje')
        
    @property
    def entity_id(self):
        return '{}-{}'.format(uname().sysname, hexlify(unique_id()).decode())
        
    @property
    def topic_prefix(self):
        return '{}/{}/{}'.format(
            self.discovery_prefix, self.component_type, self.entity_id)