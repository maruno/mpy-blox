import logging
from machine import UART

class NovaPM:
    def __init__(self, uart):
        self.uart = uart

    def start(self):
        self.uart.init(9600, timeout=5000)

    def stop(self):
        self.uart.deinit()

    def read(self):
        msg = self.uart.read(10)
        logging.debug("NovaPM: Got message %s", msg)
        assert msg[0] == ord(b'\xaa')
        assert msg[1] == ord(b'\xc0')
        assert msg[9] == ord(b'\xab')
        
        checksum = sum(v for v in msg[2:8]) % 256
        assert checksum == msg[8]

        pm2_5 = (msg[3] * 256 + msg[2]) / 10.0
        pm10 = (msg[5] * 256 + msg[4]) / 10.0
        return (pm2_5, pm10)


def main():
    from machine import UART
    nova_pm = NovaPM(UART(1, rx=4, tx=15))
    nova_pm.start()
    while True:
        data = nova_pm.read()
        logging.info('PM10=% 3.1f ug/m^3 PM2.5=% 3.1f ug/m^3', *data)


if __name__ == '__main__':
    main()