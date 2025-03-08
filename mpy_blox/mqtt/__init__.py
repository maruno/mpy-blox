# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import asyncio
from machine import WDT, unique_id
from logging import getLogger
from os import uname
from binascii import hexlify

from mpy_blox.config import config
from mpy_blox.mqtt.protocol.client import MQTT5Client
from mpy_blox.mqtt.protocol.message import MQTTMessage


logger = getLogger('mqtt')


class MQTTConnectionManager:
    _connections = {}
    def __init__(self, name):
        self.consumers_by_topic = {}
        self.name = name
        self.receive_task = None

        config_key = 'mqtt'
        if name != 'default':
            config_key += '_{}'.format(name)

        try:
            self.wdt_timeout = int(config[config_key].pop('wdt_timeout'))
        except KeyError:
            self.wdt_timeout = None

        mqtt_cfg = {}
        mqtt_cfg.update(config[config_key])

        self.mqtt_client = MQTT5Client(
            client_id=self.client_id,
            password=config[config_key + '.password'],
            **config[config_key])

    @classmethod
    def get_connection(cls, name=None):
        _connections = cls._connections
        name = name or 'default'
        if name not in _connections:
            _connections[name] = cls(name)

        return _connections[name]

    def __str__(self):
        return '<MQTTConnectionManager {}>'.format(self.name)

    @property
    def client_id(self):
        return '{}-{}'.format(uname().sysname,
                              hexlify(unique_id()).decode())

    async def subscribe(self, topic, consumer):
        consumers_by_topic = self.consumers_by_topic
        try:
            topic_consumers = consumers_by_topic[topic]
        except KeyError:
            topic_consumers = consumers_by_topic[topic] = set()

        subscribed = bool(topic_consumers)
        topic_consumers.add(consumer)
        if not subscribed:
            await self.mqtt_client.subscribe(topic)

    async def unsubscribe(self, topic, consumer):
        topic_consumers = self.consumers_by_topic.get(topic, set())
        topic_consumers.discard(consumer)
        if not topic_consumers:
            await self.mqtt_client.unsubscribe(topic)

    async def publish(self, msg: MQTTMessage):
        await self.mqtt_client.publish(msg)

    async def receive_loop(self):
        msg: MQTTMessage
        async for msg in self.mqtt_client.consume():
            topic = msg.topic
            topic_consumers = self.consumers_by_topic.get(topic, set())
            if not topic_consumers:
                # TODO Rebuild to topic filter
                logger.warning("%s Skipping message from unknown topic %s",
                               self, topic)
                continue

            # Notify all subscribed consumers of message
            logger.info("Processing message %s", msg)
            async def handle_message(msg, consumer):
                try:
                    await consumer.handle_msg(msg)
                except Exception as e:
                    logger.exception(
                        "Processing MQTT message %s to consumer %s failed",
                        msg, consumer, exc_info=e)

            await asyncio.gather(*[handle_message(msg, consumer)
                                   for consumer in topic_consumers],
                                 return_exceptions=True)


    async def connect(self):
        await self.mqtt_client.connect()
        logger.info("%s Connected")
        self.receive_task = asyncio.create_task(self.receive_loop())
        asyncio.create_task(self._delay_wdt_start())

    async def _delay_wdt_start(self):
        if not self.wdt_timeout:
            return

        logger.info("%s WDT timeout configured, will activate in 1 cycle",
                    self)
        await asyncio.sleep_ms(self.wdt_timeout)

        logger.warning("%s WDT timeout activating!", self)
        wdt = WDT(timeout=self.wdt_timeout)
        self.mqtt_client.on_pong = wdt.feed

    async def disconnect(self):
        receive_task = self.receive_task
        if receive_task is None:
            return # NO-OP, not connected?

        await self.mqtt_client.disconnect()
        receive_task.cancel()
        self.receive_task = None


class MQTTConsumer:
    def __init__(self, mqtt_connection: MQTTConnectionManager) -> None:
        self.mqtt_conn = mqtt_connection

    async def handle_msg(self, msg: MQTTMessage):
        raise NotImplementedError

    async def subscribe(self, topic):
        await self.mqtt_conn.subscribe(topic, self)

    async def unsubscribe(self, topic):
        await self.mqtt_conn.unsubscribe(topic, self)
