# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import asyncio
from collections import deque
from logging import Handler, LogRecord, getLogger
from os import remove

from mpy_blox.contextlib import suppress
from mpy_blox.log_handlers.formatter import VTSGRColorFormatter
from mpy_blox.util import rewrite_file


LOG_FILE_PATH = 'replay.log'
RS = b'\x1E'  # Record seperator control character


logger = getLogger('replay_buffer')


class ReplayBufferHandler(Handler):
    def __init__(self, max_records=150, persistence=False):
        super().__init__()

        self.processed_count = 0
        self.max_records = max_records
        self.replay_buffer = deque((), max_records)

        if persistence:
            self.reload_persisted()
            self._log_file = open(LOG_FILE_PATH, 'ab')
            self._flush_needed = asyncio.Event()
            asyncio.create_task(self._flush_task())
            logger.info("Persistence activated")
        else:
            # Clear log file if it exists
            with suppress(OSError):
                remove(file_path)
                logger.info("Removed old persistence file")

            self._log_file = self._flush_needed = None

    def reload_persisted(self):
        replay_buffer = self.replay_buffer
        # For some reason missing clear, assume empty.
        # https://github.com/micropython/micropython/blame/dd23554591ce80e1fcd47551ba6887de79c3034f/py/objdeque.c#L226-L234
        # replay_buffer.clear()
        with suppress(OSError):  # NO-OP if file doesn't exist yet
            with open(LOG_FILE_PATH, 'rb') as f:
                replay_buffer.extend(
                    f.read().rsplit(RS, self.max_records)[1:])

    def rollover_persistence(self):
        logger.info("Rolling over persistence file")
        if not self._log_file:
            return

        self._log_file.close()
        rewrite_file(LOG_FILE_PATH, RS.join(self.replay_buffer))
        self._log_file = open(LOG_FILE_PATH, 'ab')

        # Reset processed count till next rollover treshhold
        self.processed_count = 0

    async def _flush_task(self):
        try:
            flush_needed = self._flush_needed
            if not flush_needed or not self._log_file:
                return

            # Naturally flushes batches outside of sync code when signalled
            while True:
                await flush_needed.wait()
                if self.processed_count > self.max_records * 3:
                    self.rollover_persistence()
                else:
                    self._log_file.flush()
                flush_needed.clear()
        except Exception as e:
            logger.error("Persistence task died", exc_info=e)

    def emit(self, record: LogRecord):
        log_file = self._log_file
        flush_needed = self._flush_needed
        record = self.formatter.format(record)
        if log_file and flush_needed:
            log_file.write(record + RS)
            self.processed_count += 1

            # Signals a flush is needed, don't do it now
            flush_needed.set()

        self.replay_buffer.append(record)


def init_replay_buffer(config) -> deque:
    max_records = config.get('logging.replay_buffer.max_records', 150)
    persistence = config.get('logging.replay_buffer.persistence', False)
    handler = ReplayBufferHandler(max_records, persistence)
    handler.setFormatter(VTSGRColorFormatter(replay_mode=True))
    getLogger().addHandler(handler)

    return handler.replay_buffer
