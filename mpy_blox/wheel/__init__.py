# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from mpy_blox.os import makedirs


def install(wheel_file, prefix='/lib/'):
    for name, record_entry in wheel_file.wheel_record.items():
        output_path = prefix + name
        logging.info("%s -> %s", name, output_path)

        folder = output_path.rsplit('/', 1)[0]
        makedirs(folder)
        with open(output_path, 'wb') as output_f:
            output_f.write(wheel_file.read(record_entry))
