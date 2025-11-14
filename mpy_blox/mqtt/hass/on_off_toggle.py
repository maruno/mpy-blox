# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import asyncio
from logging import getLogger
from machine import Pin

from mpy_blox.mqtt.hass.disco import MQTTMutableDiscoverable


logger = getLogger('mqtt_hass')


class MQTTOnOffTogglable(MQTTMutableDiscoverable):
    def __init__(self, name, pin_id, mqtt_connection,
                 discovery_prefix = 'homeassistant'):
        super().__init__(name,
                         mqtt_connection,
                         discovery_prefix=discovery_prefix)
        self.pin = Pin(pin_id, Pin.OUT)
        self.duration_reset_task = None

    @property
    def app_state(self):
        return 'ON' if self.pin.value() else 'OFF'

    def turn_on(self):
        logger.info("%s Turning on", self)
        self.pin.value(True)
    
    def turn_off(self):
        logger.info("%s Turning off", self)
        self.pin.value(False)

    def toggle(self):
        logger.info("%s Toggling", self)
        value = self.pin.value
        new_value = not value()
        if new_value:
            self.turn_on()
        else:
            self.turn_off()

    async def reset_after_duration(self, duration):
        logger.info("%s Duration set: %ss", self, duration)
        await asyncio.sleep(duration)

        logger.info("%s Duration expired", self)
        self.turn_off()
        await self.publish_state()

    @staticmethod
    def get_unified_command(payload):
        raise NotImplementedError

    async def handle_msg(self, msg):
        cmd = self.get_unified_command(msg.payload)
        if 'state' in cmd:
            state_cmd = cmd['state']
            if state_cmd == 'ON':
                self.turn_on()
            elif state_cmd == 'OFF':
                self.turn_off()
            elif state_cmd == 'TOGGLE':
                self.toggle()

        # Reset duration task and create new one if requested
        if self.duration_reset_task:
            self.duration_reset_task.cancel()
            self.duration_reset_task = None

        if 'duration' in cmd and self.pin.value():
            self.duration_reset_task = asyncio.create_task(
                self.reset_after_duration(cmd['duration']))

        asyncio.create_task(self.publish_state())

    async def register(self):
        await super().register()
        await self.publish_state()
