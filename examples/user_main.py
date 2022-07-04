import logging
import uasyncio as asyncio


async def user_main():
    logging.info("ESP32 DEV testbed")

    while True:
        await asyncio.sleep(1)
        logging.info("Had a 1s nap")
