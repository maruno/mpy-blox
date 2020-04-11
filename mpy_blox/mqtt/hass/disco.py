import logging
import ujson
import uasyncio as asyncio
from uos import uname
from machine import Pin, unique_id
from ubinascii import hexlify

from mqtt_as import MQTTClient

from mpy_blox.config import config

DISCO_TIME = const(30)


class MQTTDiscoverable:
    component_type = None
    def __init__(self, name, msg_cb=None, discovery_prefix = 'homeassistant'):
        self.name = name
        self.discovery_prefix = discovery_prefix
        self.mqtt_client = MQTTClient(
            client_id=self.entity_id,
            subs_cb=msg_cb,
            **config['mqtt'])

    @property
    def entity_id(self):
        return '{}-{}'.format(uname().sysname, hexlify(unique_id()).decode())

    @property
    def topic_prefix(self):
        return '{}/{}/{}'.format(
            self.discovery_prefix, self.component_type, self.entity_id)

    @property
    def core_disco_config(self):
       return {
           '~': self.topic_prefix,
           'name': self.name,
           'unique_id': self.entity_id,
           'stat_t': '~/state'
        }

    @property
    def app_disco_config(self):
        raise NotImplementedError()

    async def publish_config(self):
        logging.info('Sending %s discoverability config',
                     self.__class__.__name__)

        disco_config = self.app_disco_config
        disco_config.update(self.core_disco_config)
        await self.mqtt_client.publish(
            '{}/config'.format(self.topic_prefix),
            ujson.dumps(disco_config).encode('utf-8')
        )

    @property
    def app_state(self):
        raise NotImplementedError()

    async def publish_state(self):
        await self.mqtt_client.publish(
            '{}/state'.format(self.topic_prefix),
            ujson.dumps(self.app_state)
        )

    async def disco_loop(self):
        while True:
            await self.publish_config()
            await asyncio.sleep(DISCO_TIME)

    async def connect(self):
        await self.mqtt_client.connect()
        self.disco_task = asyncio.create_task(self.disco_loop())


class MQTTMutableDiscoverable(MQTTDiscoverable):
    def __init__(self, name, msg_cb, discovery_prefix = 'homeassistant'):
        super().__init__(name, msg_cb, discovery_prefix)

    @property
    def core_disco_config(self):
        core_cfg = super().core_disco_config
        core_cfg = '~/set'
        return core_cfg
