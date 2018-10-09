import atexit
import configparser
from datetime import datetime
import logging
import time
from uuid import UUID, uuid4

import ubirch
from requests import Response
from ubirch.ubirch_protocol import UBIRCH_PROTOCOL_TYPE_REG, UBIRCH_PROTOCOL_TYPE_BIN

from ubirch_proto import Proto

# region setting up logging
logging.basicConfig(format='%(asctime)s %(name)20.20s %(levelname)-8.8s %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger("demo")
logger.setLevel(logging.INFO)

logging.getLogger("ubirch_client").setLevel(logging.INFO)
# endregion

# region config
config = configparser.ConfigParser()
config.read("demo.ini")

ub_auth = config["ubirch"]["auth"]
ub_env = config["ubirch"]["env"]


def get_from_config_or_default(section, value, make_default):
    res = config.get(section, value, fallback=None)
    if res is None:
        res = make_default()
        config[section][value] = str(res)
    return res


device_uuid = UUID(get_from_config_or_default("device", "uuid", lambda: uuid4()))
device_name = get_from_config_or_default("device", "name", lambda: "Demo Device")
device_type = get_from_config_or_default("device", "type", lambda: "demo-device")
device_hwid = UUID(get_from_config_or_default("device", "hwId", lambda: uuid4()))

identity_uuid = get_from_config_or_default("identity", "uuid", lambda: uuid4())

with open("demo.ini", "w") as f:
    config.write(f)
# endregion

# region setting up the keystore, api and the protocol
keystore = ubirch.KeyStore(device_uuid.hex + ".jks", "demo-keystore")
api = ubirch.API(ub_auth, ub_env, logger.level == logging.DEBUG)

protocol = Proto(keystore, device_uuid)
atexit.register(protocol.persist, device_uuid)
# endregion

# region identity creation
if not keystore.exists_signing_key(identity_uuid):
    keystore.create_ed25519_keypair(identity_uuid)
    reg_message = protocol.message_signed(identity_uuid, UBIRCH_PROTOCOL_TYPE_REG,
                                          keystore.get_certificate(identity_uuid))
    registration_resp = api.register_identity(reg_message)
    if registration_resp.ok:
        logger.info("registered identity {}".format(identity_uuid))
    else:
        logger.error("failed to register the identity {} ({} - {})"
                     .format(identity_uuid, registration_resp.status_code, registration_resp.content))
        exit(1)
else:
    logger.info("identity {} already exists".format(device_uuid))
# endregion

# region device creation
if not api.device_exists(device_uuid):
    d_create_resp = api.device_create({
        "deviceId": str(device_uuid),
        "deviceTypeKey": device_type,  # TODO: is that a valid key?
        "deviceName": device_name,
        "hwDeviceId": str(device_hwid),
        "tags": ["milestone-demo", "python-client"],
        "deviceProperties": {
            "storesData": True,
            "blockChain": False  # TODO: Q: what does that mean?
        },
        "created": "{}Z".format(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3])
    })

    if d_create_resp.ok:
        logger.info("created device {}".format(device_uuid))
    else:
        logger.error("failed to create the device {} ({} - {})"
                     .format(device_uuid, d_create_resp.status_code, d_create_resp.content))
        exit(1)
    # give the system some time
    time.sleep(5)
else:
    logger.info("device {} already exists".format(device_uuid))


# endregion


def send_message(uuid: UUID, payload_str: str) -> Response:
    payload = bytearray(payload_str, 'utf-8')
    message = protocol.message_chained(uuid, UBIRCH_PROTOCOL_TYPE_BIN, payload)
    return api.send(message)
