# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from micropython import const

from logging import getLogger

import struct


# Constants
SEEK_SET = const(0)
SEEK_CUR = const(1)

# Main RIFF chunk structures
RIFF_SIG = b'RIFF'
WAVE_SIG = b'WAVE'
MAIN_RIFF_CHUNK_STRUCT = '<4sI4s'
MAIN_RIFF_CHUNK_SIZE = struct.calcsize(MAIN_RIFF_CHUNK_STRUCT)

# Further RIFF chunks
RIFF_CHUNK_STRUCT = '<4sI'
RIFF_CHUNK_SIZE = struct.calcsize(RIFF_CHUNK_STRUCT)

# Format block
WAVE_FMT_BLOCK_ID = b'fmt '
WAVE_FMT_STRUCT = '<HHIIHH'
WAVE_FMT_SIZE = struct.calcsize(WAVE_FMT_STRUCT)
WAVE_PCM_FOMAT = const(1)

# Data block
WAVE_DATA_BLOCK_ID = b'data'


logger = getLogger('wave_file')


class BadWaveFile(Exception):
    pass


class WaveFile:
    def __init__(self, file_obj):
        self.file_obj = file_obj
        file_obj.seek(0, SEEK_SET)

        unpack = struct.unpack
        (riff_sig,
         remaining_size,
         wave_sig) = unpack(MAIN_RIFF_CHUNK_STRUCT,
                            file_obj.read(MAIN_RIFF_CHUNK_SIZE))

        if riff_sig != RIFF_SIG:
            raise BadWaveFile("RIFF header invalid")
        if wave_sig != WAVE_SIG:
            raise BadWaveFile("RIFF header invalid")

        # Read all RIFF block headers to find info and data
        while file_obj.tell() != remaining_size + 8:
            logger.debug("RIFF offset %s", file_obj.tell())
            (block_id,
             riff_block_size) = unpack(RIFF_CHUNK_STRUCT,
                                       file_obj.read(RIFF_CHUNK_SIZE))

            if block_id == WAVE_FMT_BLOCK_ID:
                logger.debug("Found fmt block")
                # Save wave fmt info
                (self.audio_format,
                 self.channels,
                 self.sample_rate,
                 self.byte_per_sec,
                 self.byte_per_bloc,
                 self.bits_per_sample) = unpack(WAVE_FMT_STRUCT,
                                                file_obj.read(WAVE_FMT_SIZE))
            elif block_id == WAVE_DATA_BLOCK_ID:
                logger.debug("Found data block")
                # Save wave data offset
                self.wave_offset = file_obj.tell()
                self.wave_size = riff_block_size
                file_obj.seek(riff_block_size, SEEK_CUR)
            else:
                # Skip unknown wave block, XMP/ID3 metadata?
                logger.info("Found unknown RIFF/WAVE block, skipping")
                file_obj.seek(riff_block_size, SEEK_CUR)

        self.reset()

    @property
    def remaining_data(self):
        return self.wave_size - (self.file_obj.tell() - self.wave_offset)

    @property
    def length_seconds(self):
        return self.wave_size / self.byte_per_sec

    def __str__(self) -> str:
        return "<WaveFile channels={} sample_rate={} length={}s>".format(
            self.channels,
            self.sample_rate,
            self.length_seconds)

    def reset(self):
        self.file_obj.seek(self.wave_offset, SEEK_SET)

    def read_audio(self, buffer_length_ms):
        remaining_data = self.remaining_data
        if not remaining_data:
            return

        file_obj = self.file_obj
        buff_size = int(self.byte_per_sec * buffer_length_ms / 1000)

        # Align buffer space with bloc size, preferring going up a bloc
        bloc_size = self.byte_per_bloc
        buff_size = ((buff_size + bloc_size - 1) // bloc_size) * bloc_size

        # Align with end of WAVE data
        buff_size = min(buff_size, remaining_data)
        return file_obj.read(buff_size)
