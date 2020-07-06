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
    def __init__(self, hostname, split_lines=True):
        super().__init__()
        self.split_lines = split_lines

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
        if not self.split_lines:
            return (sl_prio + msg,)

        return [sl_prio + line for line in msg.splitlines()]

    def emit(self, record):
        sock_addr = self.sock_addr
        for msg in self.format_syslog(record):
            self.sock.sendto(msg, sock_addr)


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