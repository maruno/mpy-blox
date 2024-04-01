# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import struct
from asyncio import StreamReader, StreamWriter, wait_for
from machine import UART

PROT_HEADER = const(0xAA)
PROT_TAIL = const(0xAB)
PROT_RESP_LENGTH = const(10)

SET_REPORTING_QUERY_CMD = const(0xB4020101)
QUERY_CMD = const(0xB404)
SLEEP_CMD = const(0xB4060100)
WAKEUP_CMD = const(0xB4060101)

MY_SENSOR_ADDR = const(0x151B)
COMMAND_TIMEOUT = const(2)

class NovaPM:
    def __init__(self, uart):
        self.uart = uart
        self.sr = None

    async def start(self):
        uart = self.uart
        uart.init(9600, timeout=5000)
        self.sr = StreamReader(uart)
        self.sw = StreamWriter(uart)

        # Wakeup sensor
        await self.command(struct.pack('!i', WAKEUP_CMD), MY_SENSOR_ADDR)

        # Set sensor to report on query only
        await self.command(struct.pack('!i', SET_REPORTING_QUERY_CMD),
                               MY_SENSOR_ADDR)
    
    async def command(self, packet_data, sensor_address=0xFFFF):
        packet_len = len(packet_data)
        if packet_len != 14:
            # Pad packet_data
            packet_data = packet_data + bytes((0,)) * (14 - packet_len)
        body = packet_data + struct.pack('!h', sensor_address)
        checksum = sum(v for v in body[1:]) % 256
        footer = struct.pack('!bb', checksum, PROT_TAIL)
        packet = bytes((PROT_HEADER,)) + body + footer

        logging.debug('NovaPM: Sending command %s', packet)
        sw = self.sw
        sw.write(packet)
        await sw.drain()

        # Read response
        msg = await wait_for(self.sr.read(PROT_RESP_LENGTH), COMMAND_TIMEOUT)

        if not msg:
            raise RuntimeError("NovaPM Communication timeout")

        checksum = sum(v for v in msg[2:8]) % 256
        if checksum != msg[8]:
            raise RuntimeError("NovaPM: Checksum failed")

        logging.debug("NovaPM: Got message %s", msg)
        return msg

    def stop(self):
        # Sleep sensor
        await self.command(struct.pack('!i', SLEEP_CMD), MY_SENSOR_ADDR)

        self.uart.deinit()

    async def read(self):
        msg = await self.command(struct.pack('!h', QUERY_CMD),
                                 MY_SENSOR_ADDR)
        if msg[1] != 0xC0:
            raise RuntimeError("Got unexpected packet {}".format(msg[1]))

        pm2_5 = (msg[3] * 256 + msg[2]) / 10.0
        pm10 = (msg[5] * 256 + msg[4]) / 10.0
        return (pm2_5, pm10)


async def main():
    from machine import UART
    nova_pm = NovaPM(UART(1, rx=4, tx=15))
    await nova_pm.start()
    await asyncio.sleep(10)  # Allow sensor to get fresh sample
    data = await nova_pm.read()
    logging.info('PM10=% 3.1f ug/m^3 PM2.5=% 3.1f ug/m^3', *data)

    logging.info("Putting NovaPM to sleep")
    await nova_pm.stop()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
