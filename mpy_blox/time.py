from machine import RTC

rtc = RTC()


def isotime():
    dt_tup = rtc.datetime()
    return "{}-{}-{}T{}:{}:{}.{}Z".format(*(dt_tup[0:3] + dt_tup[4:]))