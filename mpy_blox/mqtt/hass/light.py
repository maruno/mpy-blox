# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from logging import getLogger
from micropython import const
from machine import PWM
from math import ceil

from mpy_blox.mqtt.hass.on_off_toggle import MQTTOnOffTogglable


DEFAULT_DUTY = const(512)  # = 50%
PWM_FREQ = const(32000)  # = 32kHz


logger = getLogger('mqtt_hass')


class MQTTLight(MQTTOnOffTogglable):
    component_type = 'light'

    @property
    def app_state(self):
        return {
            'state': 'ON' if self.pin.value() else 'OFF'
        }

    @property
    def app_disco_config(self):
        return {'brightness': False, 'schema': 'json'}
    
    @staticmethod
    def get_unified_command(payload):
        return  payload


class MQTTDimmableLight(MQTTLight):
    def __init__(self, name, pin_id, mqtt_connection,
                 discovery_prefix = 'homeassistant'):
        super().__init__(name, pin_id, mqtt_connection, discovery_prefix)
        self._prev_duty: int | None = None
        self.pwm = PWM(self.pin, freq=PWM_FREQ, duty=0)

    @property
    def app_disco_config(self):
        return {
            'schema': 'json',
            'brightness': True,
            'brightness_scale': 1024  # Max duty cycle
        }

    @property
    def app_state(self):
        # Hass JSON Schema: brightness = duty
        duty = self.pwm.duty()
        return {
            'state': 'OFF' if duty == 0 else 'ON',
            'brightness': duty
        }

    def _turn_on(self):
        self.pwm.duty(self.get_previous_duty())

    def get_previous_duty(self) -> int:
        # TODO for ESP32, retrieve from NVS?
        prev_duty = self._prev_duty
        if prev_duty is None:
            self._prev_duty = prev_duty = DEFAULT_DUTY

        return prev_duty

    def save_previous_duty(self, prev_duty: int):
        # TODO for ESP32, persist in NVS?
        self._prev_duty = prev_duty

    def _turn_off(self):
        duty = self.pwm.duty

        # Capture and change duty ASAP
        prev_duty = duty()
        duty(0)

        # Now presist duty (If NVS is used, latency cost?)
        self.save_previous_duty(prev_duty)

    def set_brightness(self, new_brightness: float):
        if new_brightness != 0:
            logger.info("%s Setting brightness: %s%%", self, new_brightness)

        new_duty = ceil(new_brightness / 100 * 1024)
        self.pwm.duty(new_duty)

        # Now presist duty (If NVS is used, latency cost?)
        self.save_previous_duty(new_duty)

    @property
    def brightness(self) -> float:
        return self.pwm.duty() / 1024 * 100

    async def handle_msg(self, msg):
        new_duty = msg.payload.get('brightness')
        if new_duty is not None:
            self.set_brightness(new_duty / 1024 * 100)

        return await super().handle_msg(msg)
