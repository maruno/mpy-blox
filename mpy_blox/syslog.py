# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import usocket

from logging import ERROR, INFO, Handler, getLogger

from mpy_blox.contextlib import suppress

LOG_USER = 1

LOG_PRIORITIES = {
    "CRITICAL": 2,
    "DEBUG":    7,
    "ERROR":    3,
    "INFO":     6,
    "WARNING":  4,
    }

class SyslogHandler(Handler):
    def __init__(self, hostname, syslog_level=ERROR, split_lines=True):
        super().__init__()
        self.split_lines = split_lines
        self.hostname = hostname
        self.lvl = syslog_level

        try:
            addr = usocket.getaddrinfo(hostname, 514, 0, usocket.SOCK_DGRAM)[0]
        except IndexError:
            raise RuntimeError("Can't find host {}".format(hostname))

        self.sock = usocket.socket(addr[0], usocket.SOCK_DGRAM, addr[2]) 
        self.sock_addr = addr[-1]

    def __str__(self):
        return "<{} hostname={}>".format(self.__class__.__name__,
                                         self.hostname)
    
    def format_syslog(self, record):
        prio = (LOG_USER << 3) | LOG_PRIORITIES[record.levelname]
        sl_prio = "<{}>".format(prio).encode('utf-8')

        msg = self.formatter.format(record)
        if not self.split_lines:
            return (sl_prio + msg.encode('utf-8'),)

        try:
            lines = msg.splitlines()
        except AttributeError:
            lines = msg.split('\n', -1)

        return [sl_prio + line.encode('utf-8') for line in lines]

    def emit(self, record):
        if record.levelno < self.lvl:
            return

        sock_addr = self.sock_addr
        for msg in self.format_syslog(record):
            try:
                self.sock.sendto(msg, sock_addr)
            except OSError:
                print("{}: Unable to send".format(self))


def init_syslog(config):
    with suppress(KeyError):
        syslog_host = config['logging.syslog.hostname']
        try:
            syslog_level = int(config['logging.syslog.level'])
        except KeyError:
            syslog_level = ERROR
        getLogger().addHandler(SyslogHandler(syslog_host, syslog_level))


def main():
    import logging
    logging.getLogger().addHandler(SyslogHandler('172.16.3.1', INFO))
    logging.info("Test from MicroPython SyslogHandler")

if __name__ == '__main__':
    main()
