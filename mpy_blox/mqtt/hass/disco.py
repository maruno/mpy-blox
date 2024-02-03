# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import json
import uasyncio as asyncio
from uos import uname
from machine import unique_id
from ubinascii import hexlify

from mpy_blox.config import config
from mpy_blox.mqtt import MQTTConsumer
from mpy_blox.wheel import pkg_info

DISCO_TIME = const(30)


class MQTTDiscoverable(MQTTConsumer):
    _dev_registry = None
    _device_index = 0
    component_type = None
    include_top_level_device_cfg = True
    has_state = False
    is_mutable = False

    def __init__(self, name, mqtt_connection,
                 device_index=None, discovery_prefix = 'homeassistant'):
        super().__init__(mqtt_connection)

        self.name = name
        self.discovery_prefix = discovery_prefix

        if device_index:
            logging.warning("Passing device_index to %s is deprecated",
                            self.__class__)
            self.device_index = device_index
        else:
            self.device_index = MQTTDiscoverable._device_index
            MQTTDiscoverable._device_index += 1

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
        if not dev_reg:
            # Machine wide unique, cache
            unix_name = uname()
            dev_reg = {
                'name': config.get('hostname', uname().sysname),
                'manufacturer': 'MPy-BLOX',
                'model': unix_name.machine,
                'sw_version': '{} (Micropython {})'.format(
                    pkg_info('mpy-blox').version,
                    unix_name.version),
                'identifiers': [self.device_id]
            }

            if 'device.suggested_area' in config:
                dev_reg['suggested_area'] = config['device.suggested_area']

            MQTTDiscoverable._dev_registry = dev_reg

        return dev_reg

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
        await self.mqtt_conn.publish(
            topic, json.dumps(disco_config).encode('utf-8'))

    async def disco_loop(self):
        while True:
            await self.publish_config()
            await asyncio.sleep(DISCO_TIME)

    async def listen(self):
        await self.subscribe('{}/set'.format(self.topic_prefix))

    async def register(self):
        self.disco_task = asyncio.create_task(self.disco_loop())

        if self.is_mutable:
            await self.listen()


class MQTTDiscoverableState(MQTTDiscoverable):
    has_state = True
    payload_is_json = True

    @property
    def app_state(self):
        raise NotImplementedError()

    async def publish_state(self):
        if self.payload_is_json:
            payload = json.dumps(self.app_state)
        else:
            payload = self.app_state

        await self.mqtt_conn.publish(
            '{}/state'.format(self.topic_prefix),
            payload
        )


class MQTTMutableDiscoverable(MQTTDiscoverableState):
    is_mutable = True
