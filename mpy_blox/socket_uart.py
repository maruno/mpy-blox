import logging
import usocket
from machine import Pin
from uos import dupterm
from utime import sleep


class SocketUART:
    def __init__(self, uart, status_pin_id=None, port=3767):
        self.uart = uart
        self.status_pin_id = status_pin_id
        self.port = port
    
    def start(self):
        self.uart.init(115200)
    
    def stop(self):
        self.uart.deinit()
    
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
                logging.error("Unknown error handling client connection",
                              exc_info=True)
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