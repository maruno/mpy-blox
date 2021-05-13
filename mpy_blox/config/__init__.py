import logging

import uos
from ujson import load

from mpy_blox.config.secure_nvs import SecureNVS


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


secure_nvs = SecureNVS('sec_cfg')
config = OptionalSecureDict(secure_nvs)

SETTINGS_PATH = '/settings.json'
PROVISION_PATH = '/provision.json'


def read_settings(settings_path=None):
    logging.basicConfig(level=logging.DEBUG)
    try:
        with open(settings_path or SETTINGS_PATH, 'r') as settings_f:
            config = load(settings_f)
        logging.basicConfig(level=getattr(logging, config['logging.level']))
    except (KeyError, AttributeError) as e:
        if isinstance(e, AttributeError):
            logging.error("Unknown loglevel %s", config['logging.level'])
        
        logging.basicConfig(level=logging.INFO)
        logging.warning("Log level not configured, falling back to INFO")
    return config

def ingest_provision_config():
    global secure_nvs
    try:
        provision_path = PROVISION_PATH
        with open(provision_path, 'r') as provision_f:
            provision_config = load(provision_f)
    except OSError:
        return  # No new provision config

    logging.info("Ingesting provision config: %s", provision_config)
    secure_nvs.update(provision_config)
    secure_nvs.commit()

    # Provision file needs to be removed
    uos.remove(provision_path)


def init_config():
    global config
    config.update(read_settings())
    ingest_provision_config()

    return config
