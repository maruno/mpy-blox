# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from micropython import const

from machine import SPI

# Roughly max 1 MHz at 3V3, MINIMUM 10kHz
CLOCK_FREQ = const(10000)

# Chip configuration bit options
START_BIT  = const(0b00000001)
CFG_SINGLE = const(0b10000000)
CFG_CHAN0  = const(0b00000000)
CFG_CHAN1  = const(0b01000000)
CFG_MSB    = const(0b00100000)

# Mask to discard high-impedance output bits
DISCARD_MASK = const(0b1110000000000000)


class MCP3202:
    def __init__(self, chip_din, chip_dout, clk, cs, spi_id=1):
        self.chip_din = chip_din
        self.chip_dout = chip_dout
        self.clk = clk
        self.cs = cs

        # Set to sane values
        cs.on()  # CS high = chip off
        clk.off()
        chip_din.off()

        self.spi = SPI(spi_id,
                       baudrate=CLOCK_FREQ,
                       sck=self.clk,
                       mosi=self.chip_din,
                       miso=self.chip_dout,
                       polarity=0,
                       phase=1,
                       firstbit=SPI.MSB)

    def read(self, channel):
        cs = self.cs
        cs.off()  # Turns on chip

        channel_cfg = CFG_CHAN1 if channel else CFG_CHAN0
        wr_buffer = bytearray((
            START_BIT,  # Using 7 leading zeros as in section 6.1 of datasheet
            (CFG_SINGLE | channel_cfg | CFG_MSB), # Chip configuration
            0))
        self.spi.write_readinto(wr_buffer, wr_buffer)

        cs.on()  # Turns off chip

        # Parse and return result, discarding high-impedance bits
        result_view = memoryview(wr_buffer)
        logging.debug("MCP3202: Received raw data %s", bytes(result_view))

        return int.from_bytes(result_view[1:], 'big') & ~DISCARD_MASK


def main():
    import logging
    from machine import Pin
    from utime import sleep

    logging.basicConfig(level=logging.DEBUG)
    logging.info("Initialising MCP3202")
    adc_chip = MCP3202(chip_din=Pin(23, mode=Pin.OUT),
                       chip_dout=Pin(19, mode=Pin.IN),
                       clk=Pin(18, mode=Pin.OUT),
                       cs=Pin(5, mode=Pin.OUT))

    volt_div = 3.3/4096
    try:
        while True:
            sleep(0.5)
            logging.info("Reading MCP3202, channel 0...")
            result_0 = adc_chip.read(0) * volt_div
            logging.info("result: {:.3f}".format(result_0))

            result_1 = adc_chip.read(1) * volt_div
            logging.info("Reading MCP3202, channel 1...")
            logging.info("result: {:.3f}".format(result_1))
    except KeyboardInterrupt:
        adc_chip.spi.deinit()

if __name__ == '__main__':
    main()
