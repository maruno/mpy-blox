# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from mpy_blox.mqtt.hass.sensor import MQTTSensor


class MQTTNumber(MQTTSensor):
    is_mutable = True
    component_type = 'number'

    def __init__(self, name, unit, var_name,
                 set_cb,
                 mqtt_connection,
                 range_limit=None,
                 device_class=None,
                 entity_category = 'config',
                 display_mode = 'box',
                 step = 0.001,
                 discovery_prefix = 'homeassistant'):
        super().__init__(name,
                         unit, var_name,
                         mqtt_connection,
                         device_class=device_class,
                         discovery_prefix=discovery_prefix)
        self.set_cb = set_cb
        self.range_limit = range_limit
        self.entity_category = entity_category
        self.display_mode = display_mode
        self.step = step

    @property
    def app_disco_config(self):
        # Broken: disco_cfg = super().app_disco_config.getter()
        disco_cfg = {
            'entity_category': self.entity_category,
            'mode': self.display_mode,
            'step': self.step,
            'unit_of_measurement': self.unit,
            'value_template': "{{ value_json." + self.var_name + " }}"
        }

        if self.dev_cls:
           disco_cfg['device_class'] = self.dev_cls

        range_limit = self.range_limit
        if range_limit:
            disco_cfg['min'] = range_limit.start
            disco_cfg['max'] = range_limit.stop - 1

        return disco_cfg

    async def handle_msg(self, msg):
        new_value = float(msg.payload)
        self.set_variable(new_value)
        self.set_cb(new_value)
