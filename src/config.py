import configparser
import logging
import sys
from uuid import UUID, uuid4

from demo_logging import logger

config_filename = "demo.ini" if len(sys.argv) < 2 else sys.argv[1]

config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
config.read(config_filename)

ub_auth = config["ubirch"]["auth"]
ub_env = config["ubirch"]["env"]
validator_address = config["validator"]["address"]


def get_from_config_or_default(section, value, make_default, getboolean=False):
    if getboolean:
        res = config.getboolean(section, value, fallback=None)
    else:
        res = config.get(section, value, fallback=None)
    if res is None:
        res = make_default()
        if config[section] is None:
            config[section] = {}
        config[section][value] = str(res)
    return res


device_uuid = UUID(get_from_config_or_default("device", "uuid", lambda: str(uuid4())))
device_name = get_from_config_or_default("device", "name", lambda: "Demo Device")
device_type = get_from_config_or_default("device", "type", lambda: "demo-device")
device_hwid = UUID(get_from_config_or_default("device", "hwId", lambda: str(device_uuid)))

add_stdout = get_from_config_or_default("demo", "stdout", lambda: False, getboolean=True)
show_username = get_from_config_or_default("demo", "show-username", lambda: True, getboolean=True)

with open(config_filename, "w") as f:
    config.write(f)

if add_stdout:
    logger.addHandler(logging.StreamHandler(sys.stdout))