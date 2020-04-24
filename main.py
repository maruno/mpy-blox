import uasyncio as asyncio
import logging
import network
from esp import osdebug
from machine import RTC
from ntptime import settime
from utime import sleep
from uerrno import ETIMEDOUT

from mpy_blox.config import read_settings
from mpy_blox.syslog import init_syslog

rtc = RTC()

def connect_wlan(config):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(dhcp_hostname=config.get('hostname', 'espressif'))
    wlan.connect(config['wlan.ssid'], config['wlan.psk'])
    while not wlan.isconnected():
        logging.info('Waiting for WLAN connection...')
        sleep(1.0)
    
    logging.info('WLAN connected!')


def sync_ntp():
    while True:
        try:
            settime()
        except OSError as e:
            if e.args[0] != ETIMEDOUT:
                raise
        else:
            break
    logging.info('NTP time synchronised: %s', rtc.datetime())


def main():
    config = read_settings()
    logging.debug("Read config %s", config)
    
    connect_wlan(config)
    sleep(1.0)
    sync_ntp()
    init_syslog(config)
    
    # We are booted, no more need for kernel messages
    osdebug(None)
    logging.info('Mpy-BLOX succesfully booted')
    
    from user_main import user_main
    asyncio.run(user_main())


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.critical("Master exception handler, rebooting")
        from machine import reset
        reset()
