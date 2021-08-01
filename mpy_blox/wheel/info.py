# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uhashlib
from ucollections import OrderedDict

from mpy_blox.base64 import urlsafe_b64decode, urlsafe_b64encode


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


class WheelMetadata:
    def __init__(self, pep314_metadata):
        self.parsed_metadata = OrderedDict()
        for line in pep314_metadata.splitlines():
            key, value = line.split(':', 1)
            self.parsed_metadata[key] = value.strip()

    def __getitem__(self, k):
        return self.parsed_metadata[k]


class WheelRecord:
    def __init__(self, record_contents):
        self.parsed_record = parsed_record = OrderedDict()
        for line in record_contents.splitlines():
            record_entry = WheelRecordEntry(line)
            parsed_record[record_entry.name] = record_entry

    def __getitem__(self, k):
        return self.parsed_record[k]

    def __iter__(self):
        yield from self.parsed_record

    def items(self):
        yield from self.parsed_record.items()

    def __str__(self):
        return "<WheelRecord num_entries={}>".format(len(self.parsed_record))


class WheelPackage:
    def __init__(self, pep314_metadata, record_contents):
        self.metadata = WheelMetadata(pep314_metadata)
        self.wheel_record = WheelRecord(record_contents)

    @property
    def name(self):
        return self.metadata['Name']

    @property
    def version(self):
        return self.metadata['Version']

    def __str__(self):
        return "<WheelPackage name={}, version={}, wheel_record={}>".format(
            self.name,
            self.version,
            self.wheel_record)
