# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from ucollections import OrderedDict

from mpy_blox.wheel import DIST_INFO_RE
from mpy_blox.wheel.info import WheelPackage, WheelRecordEntry
from mpy_blox.zipfile import BadZipFile, ZipFile, ZipInfo


class BadWheelFile(BadZipFile):
    pass


class WheelFile(ZipFile):
    def __init__(self, file_obj):
        super().__init__(file_obj)

        dist_info_re = DIST_INFO_RE
        dist_info_path = None
        for key in self:
            m = dist_info_re.match(key)
            if m:
               self.pkg_name = m.group(3)
               self.pkg_version = m.group(4)
               dist_info_path = m.group(1)
               break

        if not dist_info_path:
            raise BadWheelFile("Missing dist-info path")

        # Read in package metadata and record
        self.package = None
        self.package = package = WheelPackage(
            self.read(dist_info_path + 'METADATA').decode(),
            self.read(dist_info_path + 'WHEEL').decode(),
            self.read(dist_info_path + 'RECORD').decode())

        logging.debug("Read wheel package: %s", package)

    @property
    def metadata(self):
        if self.package:
            return self.package.metadata
        return {}

    @property
    def wheel_info(self):
        if self.package:
            return self.package.wheel_info
        return {}

    @property
    def wheel_record(self):
        if self.package:
            return self.package.wheel_record
        return {}

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
