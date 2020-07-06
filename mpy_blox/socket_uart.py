import logging
import usocket
from machine import Pin
from uos import dupterm
from utime import sleep


class SocketUART:
    def __init__(self, uart, status_pin_id=None, port=3767, baud=115200):
        self.uart = uart
        self.status_pin_id = status_pin_id
        self.port = port
        self.baud = baud

    def serve_forever(self):
        server_socket = usocket.socket()

        addr = usocket.getaddrinfo('0.0.0.0', self.port)[0][-1]
        server_socket.bind(addr)
        server_socket.listen(1)

        logging.info("Listening on %s", addr)
        while True:
            c_socket, addr = server_socket.accept()
            logging.info("Client connected on %s", addr)
            try:
                self.serve_client(c_socket)
            except Exception:
                logging.error("Unknown error handling client connection")
            finally:
                c_socket.close()

    def serve_client(self, c_socket):
        uart = self.uart
        if self.status_pin_id:
            status_led = Pin(2, Pin.OUT)
        else:
            status_led = None
        while True:
            if not uart.any():
                continue

            if status_led:
                status_led.value(not status_led.value())
            c_socket.sendall(uart.readline())


def main():
    from machine import UART
    uart_socket = SocketUART(UART(1, rx=4, tx=15), baud=9600)
    uart_socket.serve_forever()


if __name__ == '__main__':
    main()
