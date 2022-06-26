# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

import mpy_blox.wheel as wheel
from mpy_blox.wheel.wheelfile import WheelFile

logging.basicConfig(level=logging.INFO)

logging.info("Opening WheelFile")
with open('/remote/dist/mpy_blox-latest-mpy6-bytecode-esp32.whl', 'rb') as f:
    wheel_file = WheelFile(f)
    try:
        wheel.install(wheel_file)
    except wheel.WheelExistingInstallation as ex_install_exc:
        logging.info("Force upgrading existing installation "
                     "{} -> {}".format(
                         ex_install_exc.existing_pkg.metadata['Version'],
                         wheel_file.package.metadata['Version']))
        wheel.upgrade(ex_install_exc.existing_pkg, wheel_file)
