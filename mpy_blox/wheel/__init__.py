# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import re
import uos

from mpy_blox.os import makedirs
from mpy_blox.wheel.info import WheelPackage

DIST_INFO_RE = re.compile(
    r"^(((.+?)-(.+?))(-(P\d[^-]*))?.dist-info/?)(RECORD$)?")

DEFAULT_PREFIX = '/lib/'

class WheelExistingInstallation(Exception):
    def __init__(self, pkg):
        super().__init__("Found existing installation: {}".format(pkg))
        self.existing_pkg = pkg


def read_package(dist_info_path):
    with open(dist_info_path + '/METADATA', 'rt') as metadata_f:
        pep314_metadata = metadata_f.read()
    with open(dist_info_path + '/RECORD', 'rt') as record_f:
        record_contents = record_f.read()

    return WheelPackage(pep314_metadata, record_contents)


def list_installed(prefix=None):
    prefix = prefix or DEFAULT_PREFIX
    dist_info_re = DIST_INFO_RE
    for subfolder in uos.listdir(prefix):
        m = dist_info_re.match(subfolder)
        if m:
            dist_info_path = prefix + m.group(1)
            yield read_package(dist_info_path)


def pkg_info(name, prefix=None):
    prefix = prefix or DEFAULT_PREFIX
    for pkg in list_installed(prefix):
        if pkg.name == name:
            return pkg


def install(wheel_file, prefix=None):
    prefix = prefix or DEFAULT_PREFIX
    existing_pkg = pkg_info(wheel_file.package.name, prefix)
    if existing_pkg:
        raise WheelExistingInstallation(existing_pkg)

    for name, record_entry in wheel_file.wheel_record.items():
        output_path = prefix + name
        logging.info("%s -> %s", name, output_path)

        folder = output_path.rsplit('/', 1)[0]
        makedirs(folder)
        with open(output_path, 'wb') as output_f:
            output_f.write(wheel_file.read(record_entry))
