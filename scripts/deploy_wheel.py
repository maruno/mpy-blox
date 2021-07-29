# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from mpy_blox.wheel import install
from mpy_blox.wheel.wheelfile import WheelFile

logging.basicConfig(level=logging.INFO)

logging.info("Opening WheelFile")
with open('/remote/dist/mpy_blox-latest-mpy-bytecode-esp32.whl', 'rb') as f:
    wheel_file = WheelFile(f)
    install(wheel_file)
