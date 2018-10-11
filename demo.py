import atexit
import configparser
import hashlib
import struct
import sys
from datetime import datetime, timezone, timedelta
import logging
import time
from pprint import pformat
from urllib.parse import quote
import colored
from colored import stylize
from uuid import UUID, uuid4, getnode
import base64
import msgpack
import requests
import ubirch
from requests import Response
from ubirch.ubirch_protocol import UBIRCH_PROTOCOL_TYPE_REG, UBIRCH_PROTOCOL_TYPE_BIN
from ubirch_proto import Proto
from halo import Halo

ok = stylize("✔️ ", colored.fg("green"))
nok = stylize("❌ ", colored.fg("red"))
step = stylize("▶ ", colored.fg("blue"))

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

with open("demo.ini", "w") as f:
    config.write(f)

if add_stdout:
    logger.addHandler(logging.StreamHandler(sys.stdout))


def abort():
    logger.error(stylize("Aborting!", colored.fg("red")))
    exit(1)


def wait(t, reason="Waiting..."):
    if add_stdout:
        with Halo(reason, spinner="dots"):
            time.sleep(t)
        logger.info(ok + reason + " done!")
    else:
        logger.info(reason)
        time.sleep(t)
# endregion


# region setting up the keystore, api and the protocol
keystore = ubirch.KeyStore(device_uuid.hex + ".jks", "demo-keystore")
api = ubirch.API(ub_auth, ub_env, logger.level == logging.DEBUG)

protocol = Proto(keystore, device_uuid)
atexit.register(protocol.persist, device_uuid)
# endregion

# region check the connection to ubirch api
logger.info(step + "Checking authorization")
# TODO: replace this with client api call when it's implemented
user_req = requests.get("https://auth.{}.ubirch.com/api/authService/v1/userInfo".format(ub_env), headers=api._auth)
if user_req.ok:
    username = user_req.json()["displayName"]
    logger.info(ok + "Authorized as {}".format(stylize(username, colored.fg("green"))))
else:
    logger.error(nok + "Not authorized!")
    abort()
# endregion

# region identity creation
logger.info(step + "Creating the identity")
identity_uuid = device_uuid
if not keystore.exists_signing_key(identity_uuid):
    keystore.create_ed25519_keypair(identity_uuid)
    reg_message = protocol.message_signed(identity_uuid, UBIRCH_PROTOCOL_TYPE_REG,
                                          keystore.get_certificate(identity_uuid))
    registration_resp = api.register_identity(reg_message)
    if registration_resp.ok:
        logger.info(ok + "Registered identity {}".format(stylize(identity_uuid, colored.fg("green"))))
    else:
        logger.error(nok + "Failed to register the identity {} ({} - {})"
                     .format(stylize(identity_uuid, colored.fg("blue")),
                             stylize(registration_resp.status_code, colored.fg("yellow")),
                             stylize(registration_resp.content, colored.fg("red"))))
        abort()
else:
    logger.info(ok + "Identity {} already exists".format(stylize(identity_uuid, colored.fg("blue"))))
# endregion

# region device creation
logger.info(step + "Creating the device")
if not api.device_exists(device_uuid):
    d_create_resp = api.device_create({
        "deviceId": str(device_uuid),
        "deviceTypeKey": device_type,
        "deviceName": device_name,
        "hwDeviceId": str(device_hwid),
        "tags": ["milestone-demo", "python-client"],
        "deviceProperties": {
            "storesData": True,
            "blockChain": False
        },
        "created": "{}Z".format(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3])
    })

    if d_create_resp.ok:
        logger.info(ok + "Created device {}".format(stylize(device_name, colored.fg("green"))))
    else:
        logger.error(nok + "Failed to create the device {} ({} - {})"
                     .format(stylize(device_name, colored.fg("blue")),
                             stylize(d_create_resp.status_code, colored.fg("yellow")),
                             stylize(d_create_resp.content, colored.fg("red"))))
        abort()
    # give the system some time
    time.sleep(5)
else:
    logger.info(ok + "Device {} already exists".format(stylize(device_name, colored.fg("blue"))))


# endregion


# region sending messages
logger.info(step + "Sending the message")


def send_message(uuid: UUID, payload: bytes) -> (Response, bytes):
    message = protocol.message_chained(uuid, UBIRCH_PROTOCOL_TYPE_BIN, payload)
    sig = protocol._signatures[uuid]
    return api.send(message), sig


now = datetime.now(timezone.utc)
epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)  # use POSIX epoch
posix_timestamp_micros = (now - epoch) // timedelta(microseconds=1)
posix_timestamp_millis = posix_timestamp_micros // 1000
msg = struct.pack("LLf", getnode(), posix_timestamp_millis, 900)
h = hashlib.sha512(msg).digest()
h_str = bytes.decode(base64.b64encode(h))

response, signature = send_message(device_uuid, h)
if response.ok:
    logger.info(ok + "Successfully sent {}".format(stylize(h_str, colored.fg("green"))))
    resp = msgpack.loads(response.content)
else:
    logger.error(nok + "Failed to send {} ({} - {})"
                 .format(stylize(h_str, colored.fg("blue")),
                         stylize(response.status_code, colored.fg("yellow")),
                         stylize(response.content, colored.fg("red"))))
    abort()
# endregion

wait(2, "Waiting for the message to be processed...")

# region verify the message
logger.info(step + "Validating the message with on-premise validator")
response = requests.get(validator_address + "/" + quote(h_str, safe="+="))
if response.ok:
    logger.info(ok + "Message {} successfully verified".format(stylize(h_str, colored.fg("green"))))
    logger.info(stylize(pformat(response.json()), colored.fg("green")))
else:
    logger.error(nok + "Failed to verify the message {} ({} - {})"
                 .format(stylize(h_str, colored.fg("blue")),
                         stylize(response.status_code, colored.fg("red")),
                         stylize(response.content, colored.fg("red"))))

# endregion
