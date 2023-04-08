# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import micropython
from micropython import const
from machine import SPI

from mpy_blox.sensor.adc import ADC

# Roughly max 1 MHz at 3V3, MINIMUM 10kHz
CLOCK_FREQ = const(1000000)

# Chip configuration bit options
START_BIT  = const(0b00000001)
CFG_SINGLE = const(0b10000000)
CFG_CHAN0  = const(0b00000000)
CFG_CHAN1  = const(0b01000000)
CFG_MSB    = const(0b00100000)

# Mask to discard high-impedance output bits
DISCARD_MASK = const(0b1110000000000000)

# GPIO output registers for fast access
GPIO_OUT_W1TS_REG = const(0x3FF44008)
GPIO_OUT_W1TC_REG = const(0x3FF4400C)


class MCP3202(ADC):
    needed_buffer_length = 3

    def __init__(self, chip_din, chip_dout, clk, cs, cs_pin_id, spi_id=1):
        self.chip_din = chip_din
        self.chip_dout = chip_dout
        self.clk = clk
        self.cs = cs
        self.cs_pin_id = cs_pin_id

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

        alloc_cfg_bug = self._alloc_config_buffer
        self.config_buffers = (
            alloc_cfg_bug(1),
            alloc_cfg_bug(2)
        )

    def _alloc_config_buffer(self, channel):
        channel_cfg = CFG_CHAN1 if channel else CFG_CHAN0
        return bytearray((
            START_BIT,  # Using 7 leading zeros as in section 6.1 of datasheet
            (CFG_SINGLE | channel_cfg | CFG_MSB), # Chip configuration
            0))

    @micropython.viper
    def sample_readinto(self, channel: int, buffer):
        cs_pin_bitflag: int = 1 << int(self.cs_pin_id)

        # Turn on chip
        gpio_out_w1tc_reg = ptr32(GPIO_OUT_W1TC_REG)
        gpio_out_w1tc_reg[0] = cs_pin_bitflag

        # Perform DMA write_readinto
        self.spi.write_readinto(self.config_buffers[channel-1], buffer)

        # Turn off chip
        #self.cs.on()
        gpio_out_w1ts_reg = ptr32(GPIO_OUT_W1TS_REG)
        gpio_out_w1ts_reg[0] = cs_pin_bitflag

    def parse_sample(self, sample_view):
        return int.from_bytes(sample_view[1:], 'big') & ~DISCARD_MASK

    def read(self, channel):
        wr_buffer = bytearray(self.needed_buffer_length)
        self.sample_readinto(channel, wr_buffer)

        # Parse and return result, discarding high-impedance bits
        return self.parse_sample(memoryview(wr_buffer))


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
