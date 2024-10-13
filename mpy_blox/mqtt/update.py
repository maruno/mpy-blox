# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import asyncio
from binascii import hexlify
from hashlib import sha256
from io import BytesIO
from logging import getLogger
from machine import reset
from os import remove, uname


import mpy_blox.wheel as wheel
from mpy_blox.contextlib import suppress
from mpy_blox.mqtt import MQTTConsumer
from mpy_blox.mqtt.protocol.message import MQTTMessage
from mpy_blox.wheel.wheelfile import WheelFile
from mpy_blox.util import rewrite_file


logger = getLogger('mqtt_update')

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
        logger.info("Registering as node %s with update channel: %s",
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
        logger.info("Received update list from channel: %s", msg.topic)
        self.waiting_pkgs.clear()
        for entry in msg.payload:
            update_type = entry['type']
            if update_type == 'wheel':
                self.check_wheel_update(entry)
            elif update_type == 'src':
                self.check_src_update(entry)
            else:
                logger.warning("Skipping unknown update type %s", update_type)

        if self.update_available:
            auto_update = self.auto_update
            if is_commanded:
                logger.info("Commanded to perform upgrade")
            elif auto_update:
                logger.info("Performing auto update...")

            if is_commanded or auto_update:
                await self.perform_update()
            else:
                logger.info("Updates are available, but won't act")
        else:
            self.update_done.set()

    def check_wheel_update(self, entry):
        name = entry['name']
        version = entry['version']
        installed_pkg = wheel.pkg_info(name)
        if installed_pkg and installed_pkg.version == version:
            return  # Skip unchanged packages

        # Package needs installation/update
        logger.info("Update available: %s %s -> %s",
                     name, installed_pkg.version, version)
        self.waiting_pkgs.add('wheel/' + entry['pkg_sha256'])

    def check_src_update(self, entry):
        path = entry['path']
        pkg_sha256 = entry['pkg_sha256']
        with suppress(OSError):
            with open(path, 'rb') as current_src_f:
                checksum = hexlify(sha256(current_src_f.read()).digest())
                if checksum == pkg_sha256.encode():
                    return  # Skip unchanged source

        # Source file needs installation/update
        logger.info("Update available for source file: %s", path)
        self.waiting_pkgs.add('src/' + path + '/' + pkg_sha256)

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

        pkg_type, pkg_id = pkg_id.split('/', 1)
        if pkg_type == 'src':
            self.handle_src_msg(msg, pkg_id)
        elif pkg_type == 'wheel':
            self.handle_wheel_msg(msg)
        else:
            logger.warning("Skipping unknown pkg_type")
            return

        self.pkgs_installed = True
        if not self.waiting_pkgs:
            self.update_done.set()

    def handle_src_msg(self, msg, pkg_id):
        pkg_path = '/' + pkg_id.rsplit('/', 1)[0]
        logger.info("Processing src pkg %s", pkg_path)

        rewrite_file(pkg_path, msg.raw_payload)

    def handle_wheel_msg(self, msg):
        wheel_file = WheelFile(BytesIO(msg.raw_payload))
        logger.info("Processing wheel pkg %s", wheel_file.pkg_name)

        try:
            wheel.install(wheel_file)
        except wheel.WheelExistingInstallation as ex_install_exc:
            logger.info("Force upgrading existing installation "
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
            logger.info("Finished performing update, rebooting in 3s...")
            await asyncio.sleep(3)
            reset()
