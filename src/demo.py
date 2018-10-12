import hashlib
import struct
from datetime import datetime, timezone, timedelta
import logging
import time
from pprint import pformat
from urllib.parse import quote
import colored
from colored import stylize
from uuid import UUID, getnode
import base64
import msgpack
import requests
import ubirch
from requests import Response
from ubirch.ubirch_protocol import UBIRCH_PROTOCOL_TYPE_REG, UBIRCH_PROTOCOL_TYPE_BIN

from config import device_uuid, ub_env, ub_auth, device_type, device_name, device_hwid, validator_address
from demo_logging import logger
from ubirch_proto import Proto
from util import ok, nok, step, abort, wait, shorten


# region setting up the keystore, api and the protocol
keystore = ubirch.KeyStore(device_uuid.hex + ".jks", "demo-keystore")
api = ubirch.API(ub_auth, ub_env, logger.level == logging.DEBUG)

protocol = Proto(keystore, device_uuid)
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


def send_message(uuid: UUID, payload: bytes) -> Response:
    message = protocol.message_chained(uuid, UBIRCH_PROTOCOL_TYPE_BIN, payload)
    return api.send(message)


now = datetime.now(timezone.utc)
epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)  # use POSIX epoch
posix_timestamp_micros = (now - epoch) // timedelta(microseconds=1)
posix_timestamp_millis = posix_timestamp_micros // 1000
msg = struct.pack("LLf", getnode(), posix_timestamp_millis, 900)
h = hashlib.sha512(msg).digest()
h_str = bytes.decode(base64.b64encode(h))

response = send_message(device_uuid, h)
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
    json = response.json()
    shortened = {key: shorten(json[key]) for key in json}
    logger.info(stylize(pformat(shortened), colored.fg("green")))
else:
    logger.error(nok + "Failed to verify the message {} ({} - {})"
                 .format(stylize(h_str, colored.fg("blue")),
                         stylize(response.status_code, colored.fg("red")),
                         stylize(response.content, colored.fg("red"))))

# endregion
