# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import re
import os

from mpy_blox.os import makedirs
from mpy_blox.wheel.info import WheelPackage
from mpy_blox.util import rewrite_file

DIST_INFO_RE = re.compile(
    r"^(((.+?)-(.+?))(-(P\d[^-]*))?.dist-info/?)(RECORD$)?")

DEFAULT_PREFIX = '/lib/'

class WheelExistingInstallation(Exception):
    def __init__(self, pkg):
        super().__init__("Found existing installation: {}".format(pkg))
        self.existing_pkg = pkg


class WheelUpgradeTagMismatch(Exception):
    def __init__(self, expected_tag):
        super().__init__(
            "Package tag mismatch, expected: {}".format(expected_tag))
        self.expected_tag = expected_tag


def read_package(dist_info_path):
    with open(dist_info_path + '/METADATA', 'rt') as metadata_f:
        pep314_metadata = metadata_f.read()
    with open(dist_info_path + '/WHEEL', 'rt') as wheel_info_f:
        pep314_wheel_info = wheel_info_f.read()
    with open(dist_info_path + '/RECORD', 'rt') as record_f:
        record_contents = record_f.read()

    return WheelPackage(pep314_metadata, pep314_wheel_info, record_contents)


def list_installed(prefix=None):
    prefix = prefix or DEFAULT_PREFIX
    dist_info_re = DIST_INFO_RE
    try:
        for subfolder in os.listdir(prefix):
            m = dist_info_re.match(subfolder)
            if m:
                dist_info_path = prefix + m.group(1)
                yield read_package(dist_info_path)
    except OSError:
        return ()


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


def upgrade(pkg, wheel_file, prefix=None):
    prefix = prefix or DEFAULT_PREFIX

    expected_tag = pkg.wheel_info['Tag']
    if expected_tag != wheel_file.wheel_info['Tag']:
        raise WheelUpgradeTagMismatch(expected_tag)

    processed_names = []
    for name, new_record_entry in wheel_file.wheel_record.items():
        output_path = prefix + name
        try:
            old_record_entry = pkg.wheel_record[name]
            if old_record_entry == new_record_entry:
                logging.debug("Skipping unchanged record %s", new_record_entry)
                processed_names.append(name)
                continue
        except KeyError:
            # New record, check folders
            folder = output_path.rsplit('/', 1)[0]
            makedirs(folder)

        logging.info("%s -> %s", name, output_path)
        rewrite_file(output_path, wheel_file.read(new_record_entry))

        processed_names.append(name)

    for old_name in pkg.wheel_record:
        if old_name in processed_names:
            continue  # File upgraded

        old_path = prefix + old_name
        logging.info("Removing old package file %s", old_path)
        os.remove(old_path)
    
    if wheel_file.package.version != pkg.version:
        # Remove dist-folder after version upgrade
        os.rmdir(prefix + "{}-{}.dist-info".format(wheel_file.pkg_name,
                                                   pkg.version))
