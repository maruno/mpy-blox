# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from machine import Pin

from mpy_blox.mqtt.hass.on_off_toggle import MQTTOnOffTogglable


class MQTTLight(MQTTOnOffTogglable):
    component_type = 'light'

    @property
    def app_disco_config(self):
        return {'brightness': False, 'schema': 'json'}
    
    @staticmethod
    def get_unified_command(payload):
        return  payload
