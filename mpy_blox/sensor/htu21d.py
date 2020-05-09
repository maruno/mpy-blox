from micropython import const
from uasyncio import sleep_ms
from ustruct import unpack

ADDRESS = const(0x40)
DATAGRAM_SIZE = const(3)
CMD_TEMP_MEASURE_NHM = const(0xF3)
TEMP_MEASURE_TIME_MS = const(50)
CMD_HUM_MEASURE_NHM = const(0xF5)
HUM_MEASURE_TIME_MS = const(16)

class HTU21D:
    def __init__(self, i2c):
        self.i2c = i2c
    
    async def command(self, cmd, measure_time_ms):
        i2c = self.i2c
        i2c.writeto(ADDRESS, bytes((cmd,)))
        await sleep_ms(measure_time_ms)
        data = i2c.readfrom(ADDRESS, DATAGRAM_SIZE)
        data, crc = unpack('>HB', data)
        # TODO CRC-check
        return data & 0xFFFC  # Clear the status bits
    
    async def read(self):
        raw_temp = await self.command(CMD_TEMP_MEASURE_NHM,
                                      TEMP_MEASURE_TIME_MS)
        temp = -46.85 + (175.72 * raw_temp / 65536)

        raw_hum = await self.command(CMD_HUM_MEASURE_NHM, HUM_MEASURE_TIME_MS)
        hum = -6 + (125.0 * raw_hum / 65536)

        return (temp, hum)


async def main():
    import logging
    from machine import I2C, Pin

    i2c = I2C(0, scl=Pin(22, pull=Pin.PULL_UP), sda=Pin(21, pull=Pin.PULL_UP))
    await sleep_ms(20)
    htu21d = HTU21D(i2c)
    temp, hum = await htu21d.read()

    logging.info("Read HTU21D, temperature: %s ℃, humidity: %s %%RH",
                 temp, hum)


if __name__ == '__main__':
    import uasyncio as asyncio
    asyncio.run(main())
