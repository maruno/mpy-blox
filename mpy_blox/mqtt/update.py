# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import asyncio
from hashlib import sha256
from io import BytesIO
from binascii import hexlify
from machine import reset
from os import uname


import mpy_blox.wheel as wheel
from mpy_blox.contextlib import suppress
from mpy_blox.mqtt import MQTTConsumer
from mpy_blox.mqtt.protocol.message import MQTTMessage
from mpy_blox.wheel.wheelfile import WheelFile

PREFIX = 'mpypi/'
CHANNEL_PREFIX = PREFIX + 'channels/'
PACKAGES_PREFIX = PREFIX + 'packages/'
PRIVATE_PREFIX = PREFIX + 'nodes/'


class MQTTUpdateChannel(MQTTConsumer):
    def __init__(self, channel, auto_update, mqtt_connection):
        super().__init__(mqtt_connection)
        self.channel = channel
        self.auto_update = auto_update

        self.waiting_pkgs = set()
        self.update_done = asyncio.Event()
        self.pkgs_installed = False 

    @property
    def channel_topic(self):
        return CHANNEL_PREFIX + self.channel

    @property
    def private_base(self):
        return PRIVATE_PREFIX + self.mqtt_conn.client_id + '/'

    @property
    def info_topic(self):
        return self.private_base + 'info'

    @property
    def cmd_topic(self):
        return self.private_base + 'cmd'

    @property
    def update_available(self):
        return bool(self.waiting_pkgs)

    async def register(self):
        mqtt_conn = self.mqtt_conn
        logging.info("Registering as node %s with update channel: %s",
                     mqtt_conn.client_id, self.channel)

        unix_name = uname()
        await self.mqtt_conn.publish(
            MQTTMessage(self.info_topic,
                        {
                            'uname': {
                                'sysname': unix_name.sysname,
                                'machine': unix_name.machine,
                                'version': unix_name.version
                            },
                            'versions': {
                                wheel.name: wheel.version
                                for wheel in wheel.list_installed()
                            }
                        },
                        retain=True)
        )

        # Subscribe to our private cmd topic + channel topic for updates
        await self.subscribe(self.cmd_topic)
        await self.subscribe(self.channel_topic)

    async def handle_msg(self, msg):
        topic = msg.topic
        if topic in (self.channel_topic, self.cmd_topic):
            is_commanded = topic == self.cmd_topic
            asyncio.create_task(
                self.handle_update_list_msg(msg, is_commanded))
        elif topic.startswith(PACKAGES_PREFIX):
            await self.handle_pkg_msg(msg)

    async def handle_update_list_msg(self, msg, is_commanded):
        logging.info("Received update list from channel: %s", msg.topic)
        self.waiting_pkgs.clear()
        for entry in msg.payload:
            update_type = entry['type']
            if update_type == 'wheel':
                self.check_wheel_update(entry)
            elif update_type == 'src':
                self.check_src_update(entry)
            else:
                logging.warning("Skipping unknown update type %s", update_type)

        if self.update_available:
            auto_update = self.auto_update
            if is_commanded:
                logging.info("Commanded to perform upgrade")
            elif auto_update:
                logging.info("Performing auto update...")

            if is_commanded or auto_update:
                await self.perform_update()
            else:
                logging.info("Updates are available, but won't act")
        else:
            self.update_done.set()

    def check_wheel_update(self, entry):
        name = entry['name']
        version = entry['version']
        installed_pkg = wheel.pkg_info(name)
        if installed_pkg and installed_pkg.version == version:
            return  # Skip unchanged packages

        # Package needs installation/update
        logging.info("Update available: %s %s -> %s",
                     name, installed_pkg.version, version)
        self.waiting_pkgs.add('wheel/' + entry['pkg_sha256'])

    def check_src_update(self, entry):
        path = entry['path']
        expected_checksum = entry['pkg_sha256'].encode()
        with suppress(OSError):
            with open(path, 'rb') as current_src_f:
                checksum = hexlify(sha256(current_src_f.read()).digest())
                if checksum == expected_checksum:
                    return  # Skip unchanged source

        # Source file needs installation/update
        logging.info("Update available for source file: %s", path)
        self.waiting_pkgs.add('src/' + path)

    async def handle_pkg_msg(self, msg):
        topic = msg.topic
        pkg_id = topic[len(PACKAGES_PREFIX):]
        try:
            self.waiting_pkgs.remove(pkg_id)
        except KeyError:
            # Repeated message?
            return
        finally:
            # TODO Topic filter and no subscribe/unsubscribe all the time?
            await self.unsubscribe(topic)

        pkg_type, pkg_path = pkg_id.split('/', 1)
        if pkg_type == 'src':
            self.handle_src_msg(msg, pkg_path)
        elif pkg_type == 'wheel':
            self.handle_wheel_msg(msg)
        else:
            logging.warning("Skipping unknown pkg_type")
            return

        self.pkgs_installed = True
        if not self.waiting_pkgs:
            self.update_done.set()

    def handle_src_msg(self, msg, pkg_path):
        logging.info("Processing src pkg %s", pkg_path)

        with open('/' + pkg_path, 'wb') as src_f:
            src_f.write(msg.payload)

    def handle_wheel_msg(self, msg):
        wheel_file = WheelFile(BytesIO(msg.payload))
        logging.info("Processing wheel pkg %s", wheel_file.pkg_name)

        try:
            wheel.install(wheel_file)
        except wheel.WheelExistingInstallation as ex_install_exc:
            logging.info("Force upgrading existing installation "
                         "{} -> {}".format(
                             ex_install_exc.existing_pkg.version,
                             wheel_file.package.version))
            wheel.upgrade(ex_install_exc.existing_pkg, wheel_file)

    async def perform_update(self):
        self.update_done.clear()
        if not self.update_available:
            self.update_done.set()
            return

        # Subscribe for all required updates
        for pkg_id in self.waiting_pkgs:
            # TODO Topic filter and no subscribe/unsubscribe all the time?
            await self.subscribe(PACKAGES_PREFIX + pkg_id)

        # Wait for updates to be processed
        await self.update_done.wait()

        if self.pkgs_installed:
            logging.info("Finished performing update, rebooting...")
            reset()
