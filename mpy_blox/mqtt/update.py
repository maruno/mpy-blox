# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import uasyncio as asyncio
import ujson
from io import BytesIO
from machine import unique_id
from ubinascii import hexlify
from uos import uname

from mqtt_as import MQTTClient

import mpy_blox.wheel as wheel
from mpy_blox.config import config
from mpy_blox.wheel.wheelfile import WheelFile


PREFIX = 'mpypi/'
CHANNEL_PREFIX = PREFIX + 'channels/'
PACKAGES_PREFIX = PREFIX + 'packages/'

class MQTTUpdateChannel:
    def __init__(self, channel, auto_update):
        self.channel = channel
        self.auto_update = auto_update

        self.mqtt_client = MQTTClient(
            client_id=self.device_id,
            subs_cb=self.msg_rcvd,
            password=config['mqtt.password'],
            **config['mqtt'])

        self.waiting_pkgs = set()
        self.update_done = asyncio.Event()
        self.pkgs_installed = False 

    @property
    def device_id(self):
        # TODO refactor where device_id lives?
        return '{}-{}'.format(uname().sysname,
                              hexlify(unique_id()).decode())

    @property
    def channel_topic(self):
        return CHANNEL_PREFIX + self.channel

    @property
    def update_available(self):
        return bool(self.waiting_pkgs)

    async def connect(self):
        await self.mqtt_client.connect()

        logging.info("Registering with update channel: %s", self.channel)
        await self.mqtt_client.subscribe(self.channel_topic)

    def msg_rcvd(self, topic, msg, retained):
        if topic.decode() == self.channel_topic:
            asyncio.create_task(self.pkg_list_msg_rcvd(msg))
        else:
            self.pkg_msg_rcvd(topic, msg)

    async def pkg_list_msg_rcvd(self, msg):
        logging.info("Received update list from channel: %s", self.channel)
        for entry in ujson.loads(msg):
            name = entry['name']
            version = entry['version']
            installed_pkg = wheel.pkg_info(name)
            if installed_pkg and installed_pkg.version == version:
                continue  # Skip unchanged packages

            # Package needs installation/update
            logging.info("Update available: %s %s -> %s",
                         name, installed_pkg.version, version)
            pkg_sha256 = entry['pkg_sha256']
            self.waiting_pkgs.add(pkg_sha256)

        if self.auto_update and self.update_available:
            logging.info("Performing auto update...")
            await self.perform_update()
        else:
            logging.info("No updates available")
            self.update_done.set()

    def pkg_msg_rcvd(self, topic, msg):
        pkg_sha256 = topic.decode().rsplit('/', 1)[-1]
        try:
            self.waiting_pkgs.remove(pkg_sha256)
        except KeyError:
            # Repeated message?
            return
        finally:
            pass
            # TODO Add unsubscribe to mqtt_as?
            # await self.mqtt_client.unsubscribe(PACKAGES_PREFIX + pkg_sha256)

        wheel_file = WheelFile(BytesIO(msg))
        try:
            logging.info("Processing pkg %s", wheel_file.pkg_name)
            wheel.install(wheel_file)
        except wheel.WheelExistingInstallation as ex_install_exc:
            logging.info("Force upgrading existing installation "
                         "{} -> {}".format(
                             ex_install_exc.existing_pkg.version,
                             wheel_file.package.version))
            wheel.upgrade(ex_install_exc.existing_pkg, wheel_file)

        self.pkgs_installed = True
        if not self.waiting_pkgs:
            self.update_done.set()

    async def perform_update(self):
        self.update_done.clear()
        if not self.update_available:
            self.update_done.set()
            return

        # Subscribe for all required updates
        for pkg_sha256 in self.waiting_pkgs:
            await self.mqtt_client.subscribe(PACKAGES_PREFIX + pkg_sha256)

        # Wait for updates to be processed
        await self.update_done.wait()

        if self.pkgs_installed:
            logging.info("Finished performing update")
            # Reboot?
