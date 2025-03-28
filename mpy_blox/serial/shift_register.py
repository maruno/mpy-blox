# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from machine import SPI
from utime import sleep

class SN74HC595:
    def __init__(self, ser, srclk, rclk, chain_length=1, spi_id=1):
        if chain_length != 1:
            raise NotImplementedError("SN74HC595 chaining not implemented yet")

        # Set to sane values
        ser.off()
        srclk.off()
        rclk.off()

        self.chain_length = chain_length
        self.ser = ser
        self.srclk = srclk
        self.rclk = rclk
        self.spi = SPI(spi_id,
                       baudrate=100000,
                       sck=self.srclk,
                       mosi=self.ser,
                       polarity=0,
                       phase=0,
                       firstbit=SPI.MSB)

    def write(self, value):
        if not isinstance(value, (bytes, bytearray)):
            raise ValueError("Value should be of type bytes")

        self.spi.write(value)

        self.rclk.on()
        self.rclk.off()


def main():
    from machine import Pin
    shift_register = SN74HC595(ser=Pin(23, mode=Pin.OUT),
                               srclk=Pin(18, mode=Pin.OUT),
                               rclk=Pin(4, mode=Pin.OUT))

    try:
        while True:
            shift_register.write(bytes((0, 0, 0b11001101)))
            sleep(0.5)
            #shift_register.write(bytes((0, 0b01010101,)))
            #sleep(0.5)
    except KeyboardInterrupt:
        shift_register.spi.deinit()

if __name__ == '__main__':
    main()
