# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import re
from ucollections import OrderedDict
import uhashlib

from mpy_blox.base64 import urlsafe_b64decode, urlsafe_b64encode
from mpy_blox.zipfile import BadZipFile, ZipFile, ZipInfo

DIST_INFO_RE = re.compile(
    r"^(((.+?)-(.+?))(-(P\d[^-]*))?.dist-info/)RECORD$")


class BadWheelFile(BadZipFile):
    pass


class WheelRecordEntry:
    def __init__(self, record_line):
        self.name, checksum_line, size = record_line.rsplit(',', 2)

        self.checksum = self.checksum_algo = None
        if checksum_line:
            self.checksum_algo, encoded_checksum = checksum_line.split('=', 1)
            self.checksum = urlsafe_b64decode(encoded_checksum)

        self.size =  int(size) if size else None

    @property
    def checksum_hasher(self):
        algo = self.checksum_algo
        return getattr(uhashlib, algo) if algo else None

    def __str__(self):
        return ("<WheelRecordEntry name="
                "{}, checksum_algo={}, checksum={}>".format(
                    self.name,
                    self.checksum_algo,
                    urlsafe_b64encode(self.checksum) if self.checksum else None
                ))


class WheelFile(ZipFile):
    def __init__(self, file_obj):
        super().__init__(file_obj)

        dist_info_re = DIST_INFO_RE
        self.dist_info_path = None
        for key in self:
            m = dist_info_re.match(key)
            if m:
               self.pkg_name = m.group(3)
               self.pkg_version = m.group(4)
               self.dist_info_path = m.group(1)
               break

        if not self.dist_info_path:
            raise BadWheelFile("Missing dist-info path")

        self.wheel_record = wheel_record = OrderedDict()
        raw_record = self.read(self.dist_info_path + 'RECORD')
        for line in raw_record.decode().splitlines():
            record_entry = WheelRecordEntry(line)
            wheel_record[record_entry.name] = record_entry

        logging.debug("Wheel record contains %s entries",
                      len(self.wheel_record))

    def __str__(self):
        return "<WheelFile pkg_name={}, pkg_version={}>".format(
            self.pkg_name, self.pkg_version)

    def read(self, member):
        record = None
        if isinstance(member, ZipInfo):
            zip_info = member
        elif isinstance(member, WheelRecordEntry):
            record = member
            zip_info = self[member.name]
        else:
            zip_info = self[member]

        data = super().read(zip_info)
        try:
            if not record:
                # Check the wheel record for this memeber
                record = self.wheel_record[zip_info.name]
        except KeyError:
            return data  # Extra member in ZIP, not part of wheel

        # This member is part of the wheel record, validate against it
        if len(data) != record.size and record.size is not None:
            raise BadWheelFile("Bad size for file {}".format(record.name))

        # Validate checksum
        h = record.checksum_hasher
        if h and h(data).digest() != record.checksum:
            raise BadWheelFile(
                "Bad {} for file {}".format(
                    record.checksum_algo,
                    record.name
                ))

        return data
