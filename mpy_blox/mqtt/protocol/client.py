from micropython import const

import asyncio
import logging
from asyncio import TimeoutError, wait_for
from collections import deque

from mpy_blox.future import Future
from mpy_blox.mqtt.protocol import (decode_VBI,
                                    decode_control_packet_type,
                                    encode_control_packet_fixed_header,
                                    encode_string)
from mpy_blox.mqtt.protocol.const import (
    CLEAN_FLAG, CONNACK, CONNECT, DISCONNECT, PASSWORD_FLAG, PINGRESP, PUBLISH,
    REASON_GRANTED_QOS_0, REASON_GRANTED_QOS_1, REASON_GRANTED_QOS_2,
    REASON_SUCCESS, SUBACK, SUBSCRIBE, USERNAME_FLAG) 
from mpy_blox.mqtt.protocol.exc import ErrorWithMQTTReason, MQTTConnectionRefused
from mpy_blox.mqtt.protocol.message import MQTTMessage


SYSTEM_ACK_TIMEOUT = const(10)

# TODO Tune this with properties and max receive size etc.
MAX_MSGS_WAITING = const(10)


class MQTT5Client:
    def __init__(self, server, port, client_id,
                 ssl=False, ssl_params=None,
                 username=None, password=None,
                 keep_alive_interval=None):
        self.server = server
        self.port = port
        self.client_id = client_id
        self.ssl = ssl
        self.ssl_params=ssl_params
        self.username = username
        self.password = password
        self.keep_alive_interval = keep_alive_interval

        # Communication helpers
        self.connection = None
        self.read_task = None
        self.ping_task = None
        self.ping_success = asyncio.Event()
        self.packet_futures = {}

        # Message storage
        self.msg_available = asyncio.Event()
        self.msg_deque = deque(tuple(), MAX_MSGS_WAITING)

    @property
    def next_packet_id(self):
        try:
            return max(self.packet_futures.keys()) + 1
        except ValueError:
            return 1  # No packet id's in use yet and 0 is reserved for CONNECT

    async def connect(self):
        # TODO Though convenient, not compatible with CPython Protocol
        self.connection = await asyncio.open_connection(self.server,
                                                        self.port,
                                                        self.ssl)
        self.read_task = asyncio.create_task(self._read_loop())
        if self.keep_alive_interval:
            self.ping_task = asyncio.create_task(self._ping_loop())
        await self._connect()

    async def __aenter__(self):
        await self.connect()
        return self

    async def _ping_loop(self):
        _, writer = self.connection
        write = writer.write
        drain = writer.drain
        sleep = asyncio.sleep
        ping_wait = self.ping_success.wait
        ping_clear = self.ping_success.clear()

        interval = self.keep_alive_interval / 3
        ping_attempt = 0
        while True:
            if not ping_attempt:
                await sleep(interval)
            write(encode_control_packet_fixed_header(PINGREQ, 0))
            await drain()
            
            try:
                await wait_for(ping_wait(), SYSTEM_ACK_TIMEOUT)
                ping_attempt = 0
            except TimeoutError:
                logging.warning("Ping timed out")
                ping_attempt += 1
                
            if ping_attempt > 3:
                logging.error("MQTT Keep Alive violated")
                # TODO Error handling, reconnect?

            ping_clear()

    async def _read_loop(self):
        readexactly = self.connection[0].readexactly
        ping_set = self.ping_success.set
        publish_received = self._publish_received
        suback_received = self._suback_received

        while True:
            # Read control packet type to switch
            header = (await readexactly(1))[0]
            control_packet_type = decode_control_packet_type(header)
            logging.info("Start receiving control packet %s",
                         control_packet_type)

            # Read control packet remaining length VBI
            length_vbi_idx = 0
            length_vbi_buffer = bytearray(4)  # MQTT limits to at most 4 bytes
            length_vbi_buffer[0] = (await readexactly(1))[0]
            while length_vbi_buffer[length_vbi_idx] & 128:
                length_vbi_idx += 1
                length_vbi_buffer[length_vbi_idx] = (await readexactly(1))[0]

                if length_vbi_idx > 3:
                    raise OverflowError(
                        "Malformed Variable Byte Integer in control packet")

            remaining_length = decode_VBI(length_vbi_buffer)
            logging.info("Reading %s remaining length",
                         remaining_length)
            control_packet_data = memoryview(
                await readexactly(remaining_length))

            try:
                if control_packet_type == PINGRESP:
                    ping_set()
                    continue
                if control_packet_type == PUBLISH:
                    publish_received(header, control_packet_data)
                    continue
                if control_packet_type == CONNACK:
                    self._connack_received(control_packet_data)
                    continue
                if control_packet_type == SUBACK:
                    suback_received(control_packet_data)
                    continue
                if control_packet_type == DISCONNECT:
                    self._disconnect_received(control_packet_data)
                    continue
            except Exception as e:
                logging.exception("Failed parsing/handling control packet",
                                  exc_info=e)

            logging.warning("Unknown MQTT control packet type %s",
                            control_packet_type)

    async def _connect(self, clean=True):
        _, writer = self.connection
        write = writer.write

        logging.info("Connecting to MQTT clean=%s", clean)

        # Calculate remaining length
        remaining_length = 11  # Mandatory fields variable header
        # TODO += Properties length
        # TODO += Will payload

        client_id = encode_string(self.client_id)
        remaining_length += len(client_id)

        username = None
        if self.username:
            username = encode_string(self.username)
            remaining_length += len(username)

        password = None
        if self.password:
            password = encode_string(self.password)
            remaining_length += len(password)

        # Send CONNECT control packet
        write(encode_control_packet_fixed_header(CONNECT, remaining_length))

        # CONNECT variable header: protocol name + version (5)
        write(encode_string('MQTT') + b'\x05')

        # CONNECT variable header: flags
        connect_flags = 0
        if clean:
            connect_flags |= CLEAN_FLAG
        if self.username:
            connect_flags |= USERNAME_FLAG
        if self.password:
            connect_flags |= PASSWORD_FLAG
        # TODO Will flags
        write(bytes((connect_flags,)))

        # CONNECT variable header: keep alive
        keep_alive = self.keep_alive_interval or 0
        write(keep_alive.to_bytes(2, 'big'))

        # TODO CONNECT properties
        write(b'\x00')  # No properties / 0 length

        # CONNECT payload
        write(client_id)

        # TODO Will payload

        if username:
            write(username)
        if password:
            write(password)

        # Future packet ID 0 is reserved for CONNECT
        self.packet_futures[0] = future = Future()

        await writer.drain()

        # Wait for CONNACK to be received, setting future
        session_present = await wait_for(future, SYSTEM_ACK_TIMEOUT)
        if not clean and not session_present:
            logging.warning("Session was lost")

    def _disconnect_received(self, disconnect_data):
        reason_code = disconnect_data[1]
        logging.info("Received server-side DISCONNECT reason=%s", reason_code)

        await self.close(self_initiated=False)

    def _connack_received(self, connack_data):
        future = self.packet_futures[0]  # packet ID 0 reserved for CONNECT
        reason_code = connack_data[1]
        logging.info("Received CONNACK reason=%s", reason_code)
        if reason_code != REASON_SUCCESS:
            logging.error("Server refused CONNECT")
            future.set_exception(MQTTConnectionRefused(reason_code))
        else:
            session_present = bool(connack_data[0])
            future.set_result(session_present)

        # TODO propertiestopic, msg, retained

        del self.packet_futures[0]  # packet ID 0 reserved for CONNECT

    async def subscribe(self, topic_filter):
        _, writer = self.connection
        write = writer.write
        
        # Calculate variable remaining length
        remaining_length = 4  # Mandatory fields variable header + 1 per filter
        # TODO += Properties length
        topic_filter = encode_string(topic_filter)
        remaining_length += len(topic_filter)

        # Send SUBSCRIBE control packet
        write(encode_control_packet_fixed_header(SUBSCRIBE, remaining_length))

        # SUBSCRIBE variable header: packet identifier
        packet_id = self.next_packet_id
        self.packet_futures[packet_id] = future = Future()
        write(packet_id.to_bytes(2, 'big'))

        # TODO SUBSCRIBE properties
        write(b'\x00')  # No properties / 0 length
        # TODO Subscription identifier property (optional)

        # SUBSCRIBE payload
        write(topic_filter)
        write(b'\x00')  # Subscription options

        await writer.drain()

        # Wait for SUBACK to be received
        await wait_for(future, SYSTEM_ACK_TIMEOUT)

    def _suback_received(self, suback_data):
        packet_id = int.from_bytes(suback_data[:2], 'big')
        try:
            future = self.packet_futures[packet_id]
        except KeyError:
            logging.warning("Unknown packet id %s received", packet_id)
            return

        # TODO properties

        reason_code = suback_data[-1]
        logging.info("Received SUBACK reason=%s", reason_code)
        if reason_code in (REASON_GRANTED_QOS_0,
                           REASON_GRANTED_QOS_1,
                           REASON_GRANTED_QOS_2):
            future.set_result(reason_code)
        else:
            future.set_exception(ErrorWithMQTTReason(reason_code))

        del self.packet_futures[packet_id]

    async def unsubscribe(self, topic_filter):
        logging.warning("Unsubscribe not implemented yet")

    async def publish(self, msg: MQTTMessage):
        _, writer = self.connection

        logging.info("Publishing %s", msg)
        writer.write(msg.to_packed())
        await writer.drain()

        # TODO Non-QOS 0

    def _publish_received(self, header, publish_data):
        # Decode msg using MQTTMessage class and let it await processing
        msg = MQTTMessage.from_packed(header, publish_data)
        logging.info("Received message %s", msg)

        self.msg_deque.appendleft(msg)
        self.msg_available.set()

    def consume(self):
        event = self.msg_available
        msg_deque = self.msg_deque
        class AsyncMsgGenerator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                await event.wait()
                msg = msg_deque.pop()
                if not msg_deque:
                    event.clear()

                return msg

        return AsyncMsgGenerator()


    async def close(self, self_initiated=True):
        if self_initiated:
            pass # TODO Be kind to server, send DISCONNECT

        if self.ping_task:
            self.ping_task.cancel()
        if self.read_task:
            self.read_task.cancel()

        # Close connection
        reader, writer = self.connection
        reader.close()
        writer.close()
        await asyncio.gather(reader.wait_closed(), writer.wait_closed())

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

        return exc is None
