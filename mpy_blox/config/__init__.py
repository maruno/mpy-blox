# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

import os
from json import load
logger = logging.getLogger('system')

config = {}
try:
    from mpy_blox.config.secure_nvs import SecureNVS
    offers_nvs = True
    class OptionalSecureDict(dict):
        def __init__(self, secure_dict, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self['secure'] = self.secure_dict = secure_dict

        def __getitem__(self, k):
            if k == 'secure':
                return self.secure_dict

            try:
                return self.secure_dict[k]
            except KeyError:
                return super().__getitem__(k)

    secure_nvs_store = SecureNVS('sec_cfg')
    config = OptionalSecureDict(secure_nvs_store)
except ImportError:
    # UNIX-Platform doesn't offer secure config
    offers_nvs = False

SETTINGS_PATH = '/settings.json'
PROVISION_PATH = '/provision.json'


def read_settings(settings_path=None):
    logging.basicConfig(level=logging.DEBUG)
    with open(settings_path or SETTINGS_PATH, 'r') as settings_f:
        config = load(settings_f)

    try:
        logging.basicConfig(level=getattr(logging, config['logging.level']))
    except (KeyError, AttributeError) as e:
        if isinstance(e, AttributeError):
            logger.error("Unknown loglevel %s", config['logging.level'])
        
        logging.basicConfig(level=logging.INFO)
        logger.warning("Log level not configured, falling back to INFO")
    return config

def ingest_provision_config(provision_path=None):
    global secure_nvs_store
    try:
        with open(provision_path or PROVISION_PATH, 'r') as provision_f:
            provision_config = load(provision_f)
    except OSError:
        return  # No new provision config

    logger.info("Ingesting provision config from %s", PROVISION_PATH)
    if offers_nvs:
        secure_nvs_store.update(provision_config)
        secure_nvs_store.commit()

        # Provision file needs to be removed
        os.remove(provision_path)
    else:
        # UNIX, Just put it in the unsecured config and don't remove file
        config.update(provision_config)


def init_config(unix_cwd=False):
    global config
    if unix_cwd:
        config.update(read_settings('.' + SETTINGS_PATH))
        ingest_provision_config('.' + PROVISION_PATH)
    else:
        config.update(read_settings())
        ingest_provision_config()

    return config
