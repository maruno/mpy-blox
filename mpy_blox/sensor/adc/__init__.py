# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time
import micropython

from asyncio import ThreadSafeFlag
from machine import Timer

from mpy_blox.buffer import PreAllocatedRingBuffer

class ADC:
    needed_buffer_length = 0  # Override in subclasses

    def sample_readinto(self, channel: int, buffer):
        raise NotImplementedError

    def parse_sample(self, sample_view) -> int:
        raise NotImplementedError

    def read_sample_stream(self,
                           channel,
                           sample_rate,
                           num_samples,
                           timer_id=0,
                           ring_buf_len=None):
        ring_buf_len = ring_buf_len or num_samples + 1

        # Pre-allocate for ISR
        overrun = False
        samples_collected = 0
        ring_buf = PreAllocatedRingBuffer(self.needed_buffer_length,
                                          ring_buf_len)
        ring_buf_full = ring_buf.full
        ring_buf_head_ptr = ring_buf.head_ptr
        ring_buf_advance_head = ring_buf.advance_head
        sample_readinto = self.sample_readinto
        timer = Timer(timer_id)
        tsf = ThreadSafeFlag()

        # ISR for interfacing with exact samplerate
        set_flag_every = int(ring_buf_len / 4)
        @micropython.viper
        def isr(_):
            nonlocal overrun, samples_collected

            samples_collected_loc = int(samples_collected)
            if samples_collected_loc == int(num_samples):
                timer.deinit()
                tsf.set()
                return

            overrun = ring_buf_full()
            if overrun:
                timer.deinit()
                tsf.set()
                return

            # Perform a single read into the result buffer
            sample_readinto(channel, ring_buf_head_ptr())

            # Advance buffer
            ring_buf_advance_head()
            samples_collected_loc += 1

            if samples_collected_loc % int(set_flag_every) == 0:
                # Signal main code to process results
                pass
                #tsf.set()

            # viper workaround: https://github.com/micropython/micropython/issues/8086
            samples_collected = samples_collected_loc << 1 | 1

        # Async generator reading ringbuffer if there is data
        samples_yielded = 0
        parse_sample = self.parse_sample
        rb_iter = ring_buf.iter_read()
        ring_buf_empty = ring_buf.empty
        class AsyncGenerator:
            def __aiter__(self):
                self.start = time.ticks_ms()
                return self

            async def __anext__(self):
                nonlocal rb_iter, samples_yielded
                if samples_yielded == num_samples:
                    raise StopAsyncIteration

                if overrun:
                    raise RuntimeError(
                        "Overrun at {} after yielding {}".format(
                            samples_collected, samples_yielded))

                if ring_buf_empty() or samples_yielded == 0:
                    # Wait for data from ISR and refresh iter
                    await tsf.wait()

                    end = time.ticks_ms()
                    print("Filling buffer wait took {}ms".format(time.ticks_diff(end, self.start)))
                    rb_iter = ring_buf.iter_read()

                # Parse result, discarding high-impedance bits
                result = parse_sample(next(rb_iter))

                samples_yielded += 1
                return result

        # Start ISR on a timer
        timer.init(freq=sample_rate, callback=isr)
        return AsyncGenerator()
