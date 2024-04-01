# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from micropython import const

import json
from esp32 import NVS
from machine import unique_id
from ucryptolib import aes
from uhashlib import sha256
from os import urandom

ESP_ERR_NVS_NOT_FOUND = const(-4354)
IV_SIZE = const(16)
MODE_CBC = const(2)
BLKSIZE = const(16)


class NotInitialised(Exception):
    pass


class SecureNVS(dict):
    def __init__(self, namespace, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nvs = NVS(namespace)
        self.initialised = self.read()

    def initialise(self):
        nvs = self.nvs
        iv = urandom(IV_SIZE)
        nvs.set_blob('iv', iv)

        nvs.commit()
        self.initialised = True

        return iv

    @property
    def key(self):
        return sha256(unique_id()).digest()

    @property
    def iv(self):
        try:
            iv = bytearray(IV_SIZE)
            self.nvs.get_blob('iv', iv)
        except OSError as os_e:
            if os_e.args[0] == ESP_ERR_NVS_NOT_FOUND:
                raise NotInitialised
        return iv

    @staticmethod
    def unpad(data):
        return data[0:-data[-1]]

    def read(self):
        nvs = self.nvs
        try:
            cipher = aes(self.key, MODE_CBC, self.iv)
        except NotInitialised:
            return False

        try:
            size = nvs.get_i32('payload_s')
            payload = bytearray(size)
            nvs.get_blob('payload', payload)
        except OSError as os_e:
            if os_e.args[0] == ESP_ERR_NVS_NOT_FOUND:
                return False  # Empty

        self.update(json.loads(self.unpad(cipher.decrypt(payload))))
        return True

    def clear(self):
        super().clear()

        nvs = self.nvs
        nvs.erase_key('iv')
        nvs.erase_key('payload')
        nvs.erase_key('payload_s')
        nvs.commit()

        self.initialised = False

    @staticmethod
    def pad(data):
        pad = BLKSIZE - len(data) % BLKSIZE
        return data + pad * chr(pad)

    def commit(self):
        nvs = self.nvs
        try:
            iv = self.iv
        except NotInitialised:
            iv = self.initialise()

        cipher = aes(self.key, MODE_CBC, iv)
        payload = cipher.encrypt(self.pad(json.dumps(self).encode()))
        nvs.set_i32('payload_s', len(payload))
        nvs.set_blob('payload', payload)
        nvs.commit()
