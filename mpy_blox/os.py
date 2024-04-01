# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from errno import EEXIST
import os


def makedirs(path):
    split_path = path.split('/')
    for idx, folder in enumerate(split_path):
        if not folder:
            continue

        folder_path = '/'.join(split_path[0:idx+1])
        try:
            os.mkdir(folder_path)
        except OSError as os_e:
            if os_e.errno != EEXIST:
                raise os_e
