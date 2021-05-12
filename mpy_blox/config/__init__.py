import logging

from ujson import loads

config = {}

SETTINGS_PATH = '/settings.json'


def read_settings(settings_path=None):
    logging.basicConfig(level=logging.DEBUG)
    try:
        with open(settings_path or SETTINGS_PATH, 'r') as settings_file:
            config = loads(settings_file.read())
        logging.basicConfig(level=getattr(logging, config['logging.level']))
    except (KeyError, AttributeError) as e:
        if isinstance(e, AttributeError):
            logging.error("Unknown loglevel %s", config['logging.level'])
        
        logging.basicConfig(level=logging.INFO)
        logging.warning("Log level not configured, falling back to INFO")
    return config


def init_config():
    global config
    config.update(read_settings())

    return config
