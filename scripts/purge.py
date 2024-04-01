# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os

def clean_dir(dir='/lib/'):
    if not dir.endswith('/'):
        dir += '/'
    for item in os.listdir(dir):
        full_path = dir + item
        print("Cleaning " + full_path)
        try:
            clean_dir(full_path)
            os.rmdir(full_path)
        except OSError:
            os.remove(full_path)

clean_dir()
