# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import micropython

import json

from mpy_blox.contextlib import suppress
from mpy_blox.mqtt.protocol import (
    calc_VBI_size,
    decode_VBI,
    decode_string,
    encode_control_packet_fixed_header,
    encode_string)
from mpy_blox.mqtt.protocol.const import PUBLISH


@micropython.viper
def _decode_qos(header: int) -> int:
    return (header & 0b110) >> 1


@micropython.viper
def _decode_retain(header: int) -> bool:
    # Inlined constant for viper return (header & PUBLISH_RETAIN_FLAG) == 1
    return (header & 1) == 1


class MQTTMessage:
    def __init__(self, topic=None, payload=None, qos=0, retain=False):
        # Python native properties for outgoing messages
        self.topic = topic
        self.qos = qos
        self.retain = retain
        self.packet_identifier = None

        self.raw_payload = b''
        self._payload = None
        self.payload = payload


    @property
    def payload(self):
        if not self._payload:
            raw_payload = self.raw_payload
            self._payload = raw_payload 
            with suppress(ValueError):
                # Transparently load JSON if possible
                self._payload = json.loads(raw_payload)

        return self._payload

    @payload.setter
    def payload(self, new_value):
        self._payload = new_value

        # Dump JSON if needed
        if isinstance(new_value, str):
            self.raw_payload = new_value.encode()
        elif not isinstance(new_value, bytes):
            self.raw_payload = json.dumps(new_value)

    def __str__(self) -> str:
        return "MQTTMessage<topic={}, qos={}, payload={} bytes>".format(
            self.topic, self.qos, len(self.raw_payload))

    @classmethod
    def from_packed(cls, header, packed_message):
        # Factory for incoming messages utilising packed data
        instance = cls()

        # Static header
        instance.retain = _decode_retain(header)
        instance.qos = qos = _decode_qos(header)

        # Variable header
        str_len, instance.topic = decode_string(packed_message)

        # Properties start after topic str, at str_len + uint16 offset
        prop_start = str_len + 2

        if qos != 0:
            # QoS levels 1 + 2 have a packet identifier first
            instance.packet_identifier = int.from_bytes(
                packed_message[prop_start:prop_start+2], 'big')

            # And the properties start after this
            prop_start += 2

        # TODO Decode properties
        properties_length = decode_VBI(
            packed_message[prop_start:min(prop_start+4, len(packed_message))])

        # The remainder is the payload
        variable_header_len = (prop_start
                               + calc_VBI_size(properties_length)
                               + properties_length)
        instance.raw_payload = bytes(packed_message[variable_header_len:])
        return instance

    def to_packed(self) -> bytes:
        # Calculate remaining length
        remaining_length = len(self.raw_payload)
        topic = encode_string(self.topic)
        remaining_length += len(topic)

        if self.qos != 0:
            # For packet identifier
            remaining_length += 2

        # TODO properties
        remaining_length += 1

        header = encode_control_packet_fixed_header(PUBLISH, remaining_length)
        # TODO encode and add retain and qos to header

        packet = header + topic
        if self.qos != 0:
            packet += self.packet_identifier.to_bytes(2, 'big')

        # TODO properties
        packet += b'\x00'  # No properties / 0 length

        return packet + self.raw_payload
