# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import asyncio
import json
from hashlib import sha256
from io import BytesIO
from binascii import hexlify


import mpy_blox.wheel as wheel
from mpy_blox.contextlib import suppress
from mpy_blox.mqtt import MQTTConsumer
from mpy_blox.wheel.wheelfile import WheelFile

PREFIX = 'mpypi/'
CHANNEL_PREFIX = PREFIX + 'channels/'
PACKAGES_PREFIX = PREFIX + 'packages/'


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
    def update_available(self):
        return bool(self.waiting_pkgs)

    async def register(self):
        logging.info("Registering with update channel: %s", self.channel)
        await self.subscribe(self.channel_topic)

    async def handle_msg(self, topic, msg, retained):
        if topic == self.channel_topic:
            await self.handle_update_list_msg(msg)
        elif topic.startswith(PACKAGES_PREFIX):
            await self.handle_pkg_msg(topic, msg)

    async def handle_update_list_msg(self, msg):
        logging.info("Received update list from channel: %s", self.channel)
        for entry in json.loads(msg):
            update_type = entry['type']
            if update_type == 'wheel':
                self.check_wheel_update(entry)
            elif update_type == 'src':
                self.check_src_update(entry)
            else:
                logging.warning("Skipping unknown update type %s", update_type)

        if self.auto_update and self.update_available:
            logging.info("Performing auto update...")
            await self.perform_update()
        else:
            logging.info("No updates available")
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

    async def handle_pkg_msg(self, topic, msg):
        pkg_id = topic[len(PACKAGES_PREFIX):]
        try:
            self.waiting_pkgs.remove(pkg_id)
        except KeyError:
            # Repeated message?
            return
        finally:
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
            src_f.write(msg)

    def handle_wheel_msg(self, msg):
        wheel_file = WheelFile(BytesIO(msg))
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
            await self.subscribe(PACKAGES_PREFIX + pkg_id)

        # Wait for updates to be processed
        await self.update_done.wait()

        if self.pkgs_installed:
            logging.info("Finished performing update")
            # Auto reboot based on setting?
