# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import asyncio
import ntptime
from logging import getLogger
from machine import RTC
from uerrno import ETIMEDOUT


logger = getLogger('system')
rtc = RTC()


def isotime():
    dt_tup = rtc.datetime()
    # Making subseconds max 3 long
    subseconds = str(dt_tup[-1])[:3]
    return "{}-{}-{}T{}:{}:{}.{:0<3}Z".format(*(dt_tup[0:3] + dt_tup[4:-1] + (subseconds,)))


def sync_ntp(config):
    ntp_host = config.get('ntp.host', 'pool.ntp.org')
    logger.info('Synchronising time with %s', ntp_host)

    ntptime.host = ntp_host
    while True:
        try:
            ntptime.settime()
        except OSError as e:
            if e.args[0] != ETIMEDOUT:
                raise
        else:
            break

    logger.info('NTP time synchronised')


async def scheduled_sync_task(config):
    interval = int(config.get('ntp.interval', '3600'))
    while True:
        await asyncio.sleep(interval)
        sync_ntp(config)
