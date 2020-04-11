import logging
from uasyncio import StreamReader
from machine import UART

class NovaPM:
    def __init__(self, uart):
        self.uart = uart
        self.sr = None

    def start(self):
        uart = self.uart
        uart.init(9600, timeout=5000)
        self.sr = StreamReader(uart)

    def stop(self):
        self.uart.deinit()

    async def read(self):
        valid_msg = False
        while not valid_msg:
            msg = await self.sr.read(10)
            if not msg:
                continue
            valid_msg = (msg[0] == ord(b'\xaa')
                         and msg[1] == ord(b'\xc0')
                         and msg[9] == ord(b'\xab'))
            if valid_msg:
                checksum = sum(v for v in msg[2:8]) % 256
                valid_msg = checksum == msg[8]

        logging.debug("NovaPM: Got message %s", msg)
        pm2_5 = (msg[3] * 256 + msg[2]) / 10.0
        pm10 = (msg[5] * 256 + msg[4]) / 10.0
        return (pm2_5, pm10)


async def main():
    from machine import UART
    nova_pm = NovaPM(UART(1, rx=4, tx=15))
    nova_pm.start()
    while True:
        data = nova_pm.read()
        logging.info('PM10=% 3.1f ug/m^3 PM2.5=% 3.1f ug/m^3', *data)


if __name__ == '__main__':
    import uasyncio as asyncio
    asyncio.run(main())