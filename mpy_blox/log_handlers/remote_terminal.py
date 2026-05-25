# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import asyncio
from logging import Handler, LogRecord, getLogger

from mpy_blox.log_handlers.formatter import (VTSGRColorFormatter,
                                             FG_GREY, RESET,
                                             get_sgr_escape)


logger = getLogger('remote_vt')


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
            logger.exception("Remote terminal %s disconnected?",
                             self.peername, exc_info=e)

    async def replay(self, replay_buffer):
        drain_buffer = b''
        record_count = 0
        for record in replay_buffer:
            drain_buffer += record + '\n'
            record_count += 1

            # Drain every 10 lines
            if (record_count % 10) == 0:
                await self.write(drain_buffer)
                drain_buffer = b''

        drain_buffer += (get_sgr_escape(FG_GREY)
                         + b'--- End of log replay ---'
                         + get_sgr_escape(RESET) + b'\n');
        await self.write(drain_buffer)


class RemoteTerminalHandler(Handler):
    def __init__(self, host, port, replay_buffer = None):
        super().__init__()

        self.host = host
        self.port = port
        self.remote_conns = []
        self.drain_event = asyncio.Event()

        self.buffer = b''
        self.replay_buffer = replay_buffer

    def emit(self, record: LogRecord):
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
        remote_conn = RemoteTerminalConnection(writer, peername)
        self.remote_conns.append(remote_conn)

        if self.replay_buffer:
            await remote_conn.replay(self.replay_buffer)

        # Log after, so remote conn sees connection established
        logger.info("Remote terminal %s connected", peername)

    async def serve(self):
        asyncio.create_task(self.drain_buffer_task())
        await asyncio.start_server(self.handle_new_client,
                                   self.host, self.port)
        # TODO Handle network outages and cleaning/recreating server


async def init_remote_terminal(config, replay_buffer):
    host = config['logging.remote_terminal.listen_host']
    port = int(config.get('logging.remote_terminal.listen_port', '8023'))
    handler = RemoteTerminalHandler(host, port, replay_buffer)
    handler.setFormatter(VTSGRColorFormatter())
    await handler.serve() 
    getLogger().addHandler(handler)
