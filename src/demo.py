import hashlib
from datetime import datetime, timezone, timedelta
import logging
import time
from urllib.parse import quote
import colored
from colored import stylize
from uuid import UUID
import base64
import msgpack
import requests
import ubirch
from requests import Response
from ubirch.ubirch_protocol import UBIRCH_PROTOCOL_TYPE_REG, UBIRCH_PROTOCOL_TYPE_BIN

from config import device_uuid, ub_env, ub_auth, device_type, device_name, device_hwid, validator_address
from demo_logging import logger
from ubirch_proto import Proto
from util import ok, nok, step, abort, wait, shorten, make_sensitive_message

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
        # you can put group uuids here, so other users see the device
        "groups": ["db1488ae-becc-40a3-a5c2-b6daadd6715b"],
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

# region sending an ordinary message
logger.info(step + "Sending some ordinary messages to ubirch")


def check_response(response, type):
    if response.ok:
        logger.info(ok + "{} - message successfully sent".format(type))
    else:
        logger.error(nok + "{} - failed to send the message ({} - {})"
                     .format(type, response.status_code, response.content))


now = datetime.now(timezone.utc)
epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)  # use POSIX epoch
posix_timestamp_micros = (now - epoch) // timedelta(microseconds=1)

# 0x32 - a measurement starting with a timestamp...
message0 = protocol.message_chained(device_uuid, 0x32, [posix_timestamp_micros, 42, 1337])
resp0 = api.send(message0)
check_response(resp0, "\t0x32 (single)")

# ... or an array of such measurements
message1 = protocol.message_chained(device_uuid, 0x32, [
    [posix_timestamp_micros, 42, 1337],
    [posix_timestamp_micros + 1e6, 7, 666]
])
resp1 = api.send(message1)
check_response(resp1, "\t0x32 (multi) ")

# 0x53 - generic sensor message - just send a json
message2 = protocol.message_chained(device_uuid, 0x53, {"message": "Hello World!", "foo": 42})
resp2 = api.send(message2)
check_response(resp2, "\t0x53 (json)  ")

# 0x00 - binary message
message3 = protocol.message_chained(device_uuid, 0x00, b"just some bytes")
resp3 = api.send(message3)
check_response(resp3, "\t0x00 (binary)")

# a message that's not chained to the previous messages
message4 = protocol.message_signed(device_uuid, 0x00, b"some other bytes")
resp4 = api.send(message4)
check_response(resp4, "\tnon-chained message")

if all(map(lambda r: r.ok, [resp0, resp1, resp2, resp3, resp4])):
    logger.info(ok + "Successfully sent all the messages")
else:
    logger.error(nok + "Some messages failed")
# endregion

# region sealing the payload
logger.info(step + "Sealing a sensitive message")


# we're sending only the hash of our message to ubirch!
# this is useful, because we then can use ubirch to validate if our message has got to the other side unchanged
def seal(uuid: UUID, payload: bytes) -> Response:
    payload_hash = hashlib.sha512(payload).digest()
    message = protocol.message_chained(uuid, UBIRCH_PROTOCOL_TYPE_BIN, payload_hash)
    return api.send(message)


msg = make_sensitive_message()
msg_b64 = bytes.decode(base64.b64encode(msg))

response = seal(device_uuid, msg)
if response.ok:
    logger.info(ok + "Successfully sealed message {}".format(stylize(msg_b64, colored.fg("green"))))
    resp = msgpack.loads(response.content)
else:
    logger.error(nok + "Failed to seal message {} ({} - {})"
                 .format(stylize(msg_b64, colored.fg("blue")),
                         stylize(response.status_code, colored.fg("yellow")),
                         stylize(response.content, colored.fg("red"))))
    abort()

wait(2, "Waiting for the seal to be processed...")

logger.info(step + "Sending the message {} to our super-secret backend".format(stylize(msg_b64, colored.fg("blue"))))
secret_backend = {}
secret_backend["secret_message"] = msg
# endregion

logger.info(stylize("... meanwhile in the super-secret backend ...", colored.fg("orange_1")))

# region verify the message
srvr = stylize("sec-srvr> ", colored.fg("yellow"))

received_message = secret_backend["secret_message"]
received_message_b64 = bytes.decode(base64.b64encode(received_message))
logger.info(srvr + "Received a super-secret message {}".format(stylize(received_message_b64, colored.fg("blue"))))

logger.info(srvr + step + "Validating the message with on-premise validator")
received_message_hash = bytes.decode(base64.b64encode(hashlib.sha512(received_message).digest()))
response = requests.get(validator_address + "/" + quote(received_message_hash, safe="+="))

if response.ok:
    logger.info(srvr + ok + "Message {} successfully verified"
                .format(stylize(received_message_b64, colored.fg("green"))))
    json = response.json()
    shortened = {key: shorten(json[key]) for key in json}
    logger.info(srvr + "Relevant proof information (shortened):")
    logger.info(srvr + stylize(shortened, colored.fg("blue")))
else:
    logger.error(srvr + nok + "Failed to verify the message {} ({} - {})"
                 .format(stylize(received_message_b64, colored.fg("blue")),
                         stylize(response.status_code, colored.fg("red")),
                         stylize(response.content, colored.fg("red"))))

# endregion
