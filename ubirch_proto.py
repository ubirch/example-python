import atexit
import hashlib
import logging
import pickle
from datetime import datetime
from time import sleep
from uuid import UUID

import ubirch
from requests import Response
from ubirch.ubirch_protocol import UBIRCH_PROTOCOL_TYPE_BIN, UBIRCH_PROTOCOL_TYPE_REG

logger = logging.getLogger(__name__)


class Proto(ubirch.Protocol):
    def __init__(self, key_store: ubirch.KeyStore, uuid: UUID) -> None:
        super().__init__()
        self.__ks = key_store
        self.load(uuid)
        logger.info("ubirch-protocol: device id: {}".format(uuid))

    def persist(self, uuid: UUID):
        signatures = self.get_saved_signatures()
        with open(uuid.hex + ".sig", "wb") as f:
            pickle.dump(signatures, f)

    def load(self, uuid: UUID):
        try:
            with open(uuid.hex + ".sig", "rb") as f:
                signatures = pickle.load(f)
                logger.info("loaded {} known signatures".format(len(signatures)))
                self.set_saved_signatures(signatures)
        except Exception as _e:
            logger.warning("no existing saved signatures")
            pass

    def _sign(self, uuid: UUID, message: bytes) -> bytes:
        return self.__ks.find_signing_key(uuid).sign(message)

    def _verify(self, uuid: UUID, message: bytes, signature: bytes) -> None:
        vk = self.__ks.find_verifying_key(uuid)
        # TODO: remove this line after https://github.com/ubirch/ubirch-protocol-python/pull/5 gets merged and published
        message = hashlib.sha512(message).digest()
        vk.verify(signature, message)
