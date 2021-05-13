import uasyncio as asyncio
import logging
import network
import ntptime
from esp import osdebug
from machine import RTC
from sys import print_exception
from uerrno import ETIMEDOUT
from uio import StringIO
from utime import sleep

from mpy_blox.config import init_config
from mpy_blox.syslog import init_syslog

rtc = RTC()

def connect_wlan(config):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(dhcp_hostname=config.get('hostname', 'espressif'))

    secure_cfg = config['secure']
    wlan.connect(secure_cfg['wlan.ssid'], secure_cfg['wlan.psk'])
    while not wlan.isconnected():
        logging.info('Waiting for WLAN connection...')
        sleep(1.0)
    
    logging.info('WLAN connected!')


def sync_ntp(config):
    ntp_host = config.get('ntp.host', 'pool.ntp.org')
    logging.info('Synchronising time with %s', ntp_host)

    ntptime.host = ntp_host
    while True:
        try:
            ntptime.settime()
        except OSError as e:
            if e.args[0] != ETIMEDOUT:
                raise
        else:
            break
    logging.info('NTP time synchronised: %s', rtc.datetime())


def main():
    config = init_config()
    logging.debug("Read config %s", config)
    
    connect_wlan(config)
    sleep(1.0)
    sync_ntp(config)
    init_syslog(config)
    
    # We are booted, no more need for kernel messages
    osdebug(None)
    logging.info('Mpy-BLOX succesfully booted')
    
    from user_main import user_main
    asyncio.run(user_main())


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.critical(
            "Master exception handler, rebooting...\n")

        exception_info_io = StringIO()
        print_exception(e, exception_info_io)
        logging.critical(
            "%s: %s, Exception info follows\n\n%s",
            e.__class__.__name__, e,
            exception_info_io.getvalue())

        from machine import reset
        reset()
