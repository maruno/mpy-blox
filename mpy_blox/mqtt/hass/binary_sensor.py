# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import asyncio

from mpy_blox.mqtt.hass.disco import MQTTDiscoverableState


class MQTTBinarySensor(MQTTDiscoverableState):
    component_type = 'binary_sensor'

    def __init__(self, name, var_name,
                 mqtt_connection,
                 device_class=None,
                 discovery_prefix = 'homeassistant'):
        super().__init__(name,
                         mqtt_connection,
                         discovery_prefix=discovery_prefix)
        self.var_name = var_name
        self.dev_cls = device_class
        self.state = None
        self.disco_task = None

    @property
    def app_disco_config(self):
        disco_cfg = {
            'value_template': "{{ value_json." + self.var_name + " }}"
        }

        if self.dev_cls:
           disco_cfg['device_class'] = self.dev_cls

        return disco_cfg

    def set_variable(self, var_value):
        self.var_value = 'ON' if var_value is True else 'OFF'
        create_task(self.publish_state())

    @property
    def app_state(self):
        return {
            self.var_name: self.var_value
        }
