# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

class suppress:
    def __init__(self, *exceptions):
        self.suppressed_excs = exceptions

    def __enter__(self):
        pass  # NO-OP

    def __exit__(self, exc_type, exc_val, tb):
        return (exc_type is not None
                and issubclass(exc_type, self.suppressed_excs))
