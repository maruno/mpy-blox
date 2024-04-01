# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import logging
import asyncio
from machine import unique_id
from os import uname
from binascii import hexlify

from mpy_blox.config import config
from mpy_blox.contextlib import suppress


class MQTTConsumer:
    def __init__(self, mqtt_connection) -> None:
        self.mqtt_conn = mqtt_connection

    async def handle_msg(self, topic, msg, retained):
        raise NotImplementedError

    async def subscribe(self, topic):
        await self.mqtt_conn.subscribe(topic, self)

    async def unsubscribe(self, topic):
        await self.mqtt_conn.unsubscribe(topic, self)


class MQTTConnectionManager:
    _connections = {}
    def __init__(self, name):
        self.consumers_by_topic = {}
        self.name = name
        self.receive_task = None

        config_key = 'mqtt'
        if name != 'default':
            config_key += '_{}'.format(name)

        mqtt_cfg = {}
        mqtt_cfg.update(config[config_key])
        queue_len = mqtt_cfg.pop('queue_len', 5)

        self.mqtt_client = MQTTClient(
            client_id=self.client_id,
            queue_len=queue_len,
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

    async def publish(self, topic, message, qos=0):
        if isinstance(message, str):
            message = message.encode()
        elif not isinstance(message, bytes):
            message = json.dumps(message).encode()

        await self.mqtt_client.publish(topic, message, qos=qos)

    async def receive_loop(self):
        async for topic, msg, retained in self.mqtt_client.queue:
            topic = topic.decode()
            topic_consumers = self.consumers_by_topic.get(topic, set())
            if not topic_consumers:
                logging.warning("%s Skipping message from unknown topic",
                                self, self.name)
                continue
            
            logging.info("%s Received %s bytes message for topic %s",
                         self, len(msg), topic)
            with suppress(ValueError):
                # Transparently load JSON if possible
                msg = json.loads(msg)

            # Notify all subscribed consumers of message
            await asyncio.gather(*[consumer.handle_msg(topic, msg, retained)
                                   for consumer in topic_consumers])

    async def connect(self):
        await self.mqtt_client.connect()
        self.receive_task = asyncio.create_task(self.receive_loop())

    # TODO Connection log?

    async def disconnect(self):
        receive_task = self.receive_task
        if receive_task is None:
            return # NO-OP, not connected?

        await self.mqtt_client.disconnect()
        receive_task.cancel()
        self.receive_task = None
