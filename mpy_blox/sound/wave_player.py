# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from logging import getLogger

import asyncio
from machine import I2S, Pin
from math import ceil

from mpy_blox.sound.wave_file import WAVE_PCM_FOMAT


logger = getLogger('wave_player')


class UnsupportedWaveFile(Exception):
    pass


class WavePlayer:
    def __init__(self,
                 sck_pin=14,  # eq.: I2C SCL, MAX98357 BCLK
                 ws_pin=13,  # eq.: MAX98357 LRCLK
                 sd_pin=12,
                 buffer_length_ms = 250):  # eq.L: I2C SDA, MAX98357 DIN
        self.sck_pin = Pin(sck_pin)
        self.ws_pin = Pin(ws_pin)
        self.sd_pin = Pin(sd_pin)
        self.buffer_length_ms = buffer_length_ms

        self.i2s = None

    def _init_i2s_for(self, wave_file):
        init_args = {
            'sck': self.sck_pin,
            'ws': self.ws_pin,
            'sd': self.sd_pin,
            'mode': I2S.TX,
            'bits': wave_file.bits_per_sample,
            'format': I2S.STEREO if wave_file.channels == 2 else I2S.MONO,
            'rate': wave_file.sample_rate,
            'ibuf': int(wave_file.byte_per_sec * self.buffer_length_ms / 1000)
        }
        if not self.i2s:
            self.i2s = I2S(0, **init_args)
        else:
            self.i2s.init(**init_args)

        return self.i2s

    async def play_wave(self, wave_file):
        logger.info("Playing wave file: %s", wave_file)

        if wave_file.audio_format != WAVE_PCM_FOMAT:
            raise UnsupportedWaveFile("Only PCM supported")

        if wave_file.channels > 2:
            raise UnsupportedWaveFile("Only stereo or mono supported")

        # Reset wave_file and init I2S against it
        read_size_ms = ceil(self.buffer_length_ms / 2)
        wave_file.reset()
        i2s = self._init_i2s_for(wave_file)
        s_writer = asyncio.StreamWriter(i2s)

        # Play wave according to playback rate
        sleep_ms = asyncio.sleep_ms
        s_write = s_writer.write
        s_drain = s_writer.drain
        while(wave_file.remaining_data):
            s_write(wave_file.read_audio(read_size_ms))
            await s_drain()

            # Conservative sleep with playback rate to prevent underrun
            await sleep_ms(read_size_ms - 50)
