# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from machine import RTC

rtc = RTC()


def isotime():
    dt_tup = rtc.datetime()
    return "{}-{}-{}T{}:{}:{}.{}Z".format(*(dt_tup[0:3] + dt_tup[4:]))
