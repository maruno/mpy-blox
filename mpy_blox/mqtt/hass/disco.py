# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import ujson
import uasyncio as asyncio
from machine import unique_id
from ubinascii import hexlify
from uos import uname

from mqtt_as import MQTTClient

from mpy_blox.config import config
from mpy_blox.wheel import pkg_info

DISCO_TIME = const(30)


class MQTTDiscoverable:
    _dev_registry = None
    component_type = None
    include_top_level_device_cfg = True
    has_state = False
    is_mutable = False

    def __init__(self, name, msg_cb=None,
                 device_index=None, discovery_prefix = 'homeassistant'):
        self.name = name
        self.discovery_prefix = discovery_prefix
        self.device_index = device_index
        self.mqtt_client = MQTTClient(
            client_id=self.entity_id,
            subs_cb=msg_cb,
            password=config['mqtt.password'],
            **config['mqtt'])

    @property
    def device_id(self):
        return '{}-{}'.format(uname().sysname,
                              hexlify(unique_id()).decode())

    @property
    def entity_id(self):
        device_index = self.device_index
        if device_index:
            return '{}-{}'.format(self.device_id, device_index)

        return self.device_id

    @property
    def dev_registry(self):
        dev_reg = MQTTDiscoverable._dev_registry
        entity_id = self.entity_id
        if not dev_reg:
            # Machine wide unique, cache
            unix_name = uname()
            dev_reg = {
               'manufacturer': 'Mpy-BLOX',
               'model': unix_name.machine,
               'sw_version': '{} (Micropython {})'.format(
                   pkg_info('mpy-blox').version,
                   unix_name.version)
            }

            if 'device.suggested_area' in config:
                dev_reg['suggested_area'] = config['device.suggested_area']

            MQTTDiscoverable._dev_registry = dev_reg

        entity_reg = {
            'name': self.name,
            'identifiers': [entity_id]
        }
        entity_reg.update(dev_reg)

        device_id = self.device_id
        if device_id != entity_id:
           entity_reg['via_device'] = device_id

        return entity_reg

    @property
    def topic_prefix(self):
        return '{}/{}/{}'.format(
            self.discovery_prefix, self.component_type, self.entity_id)

    @property
    def core_disco_config(self):
        core_cfg = {
            '~': self.topic_prefix,
            'device': self.dev_registry
        }

        if self.include_top_level_device_cfg:
            core_cfg['name'] = self.name
            core_cfg['unique_id'] = self.entity_id

        if self.has_state:
            core_cfg['stat_t'] = '~/state'

        if self.is_mutable:
            core_cfg['cmd_t'] = '~/set'

        return core_cfg

    @property
    def app_disco_config(self):
        raise NotImplementedError()

    async def publish_config(self):
        topic = '{}/config'.format(self.topic_prefix)
        logging.info('Sending %s discoverability config to %s',
                     self.__class__.__name__, topic)

        disco_config = self.app_disco_config
        disco_config.update(self.core_disco_config)
        await self.mqtt_client.publish(
            topic, ujson.dumps(disco_config).encode('utf-8'))

    async def disco_loop(self):
        while True:
            await self.publish_config()
            await asyncio.sleep(DISCO_TIME)

    async def connect(self):
        await self.mqtt_client.connect()
        self.disco_task = asyncio.create_task(self.disco_loop())

    async def disconnect(self):
        self.disco_task.cancel()
        await self.mqtt_client.disconnect()


class MQTTDiscoverableState(MQTTDiscoverable):
    has_state = True

    @property
    def app_state(self):
        raise NotImplementedError()

    async def publish_state(self):
        await self.mqtt_client.publish(
            '{}/state'.format(self.topic_prefix),
            ujson.dumps(self.app_state),
            qos=1
        )

class MQTTMutableDiscoverable(MQTTDiscoverableState):
    is_mutable = True
