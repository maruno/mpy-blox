# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import ntptime
from machine import RTC
from uerrno import ETIMEDOUT

rtc = RTC()


def isotime():
    dt_tup = rtc.datetime()
    return "{}-{}-{}T{}:{}:{}.{}Z".format(*(dt_tup[0:3] + dt_tup[4:]))


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
