# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import asyncio
import logging
from logging import Handler, getLogger

from mpy_blox.log_handlers.formatter import VTSGRColorFormatter


class RemoteTerminalConnection:
    def __init__(self, writer, peername):
        self.writer = writer
        self.broken = False
        self.peername = peername

    async def write(self, data):
        writer = self.writer
        try:
            writer.write(data)

            # Micropython specific quirk: Write isn't guaranteed to go out sometime
            if writer.out_buf:
                # Explicitly drain if not everything was written, to write out_buf
                await writer.drain()
        except Exception as e:
            self.broken = True
            logging.exception("Remote terminal %s disconnected?",
                              self.peername, exc_info=e)


class RemoteTerminalHandler(Handler):
    def __init__(self, host, port):
        super().__init__()

        self.host = host
        self.port = port
        self.remote_conns = []
        self.buffer = b''
        self.drain_event = asyncio.Event()

    def emit(self, record):
        if not self.remote_conns:
            return  # NO-OP when nobody is connected

        self.buffer += self.formatter.format(record) + b'\n'
        self.drain_event.set()

    async def drain_buffer_task(self):
        drain_event = self.drain_event
        while True:
            await drain_event.wait()
            while self.buffer:  # Loop on buffer, cause it could be refilled
                # Copy buffer and write out
                send_buf = self.buffer
                self.buffer = b''
                await asyncio.gather(*(remote_conn.write(send_buf)
                                       for remote_conn in self.remote_conns))

                # Remove any broken terminals
                self.remote_conns = [remote_conn
                                     for remote_conn in self.remote_conns
                                     if not remote_conn.broken]

            # Buffer is now empty, reset event
            drain_event.clear()

    async def handle_new_client(self, _, writer):
        peername = writer.get_extra_info('peername')
        self.remote_conns.append(RemoteTerminalConnection(writer, peername))
        # Log after, so remote conn sees connection established
        logging.info("Remote terminal %s connected", peername)

    async def serve(self):
        asyncio.create_task(self.drain_buffer_task())
        await asyncio.start_server(self.handle_new_client,
                                   self.host, self.port)
        # TODO Handle network outages and cleaning/recreating server


async def init_remote_terminal(config):
    host = config['logging.remote_terminal.listen_host']
    port = int(config.get('logging.remote_terminal.listen_port', '8023'))
    handler = RemoteTerminalHandler(host, port)
    handler.setFormatter(VTSGRColorFormatter())
    await handler.serve() 
    getLogger().addHandler(handler)
