# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

class ErrorWithMQTTReason(Exception):
    def __init__(self, reason_code, *args: object) -> None:
        super().__init__(*args)
        self.reason_code = reason_code

    def __str__(self) -> str:
        return "{}, reason code {}".format(self.__class__, self.reason_code)


class MQTTConnectionRefused(ErrorWithMQTTReason):
    pass

