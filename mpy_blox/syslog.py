import usocket

from logging import Handler, getLogger

LOG_USER = 1

LOG_PRIORITIES = {
    "CRITICAL": 2,
    "DEBUG":    7,
    "ERROR":    3,
    "INFO":     6,
    "WARNING":  4,
    }

class SyslogHandler(Handler):
    def __init__(self, hostname):
        super().__init__()
        try:
            addr = usocket.getaddrinfo(hostname, 514, 0, usocket.SOCK_DGRAM)[0]
        except IndexError:
            raise RuntimeError("Can't find host {}".format(hostname))

        self.sock = usocket.socket(addr[0], usocket.SOCK_DGRAM, addr[2]) 
        self.sock_addr = addr[-1]
    
    def format_syslog(self, record):
        prio = (LOG_USER << 3) | LOG_PRIORITIES[record.levelname]
        sl_prio = "<{}>".format(prio).encode('utf-8')
        msg = self.formatter.format(record).encode('utf-8') 
        return sl_prio + msg

    def emit(self, record):
        self.sock.sendto(self.format_syslog(record), self.sock_addr)


def init_syslog(config):
    try:
        syslog_host = config['logging.syslog.hostname']
        getLogger().addHandler(SyslogHandler(syslog_host))
    except KeyError:
        pass


def main():
    import logging
    logging.getLogger().addHandler(SyslogHandler('172.16.3.1'))
    logging.info("Test from MicroPython SyslogHandler")

if __name__ == '__main__':
    main()