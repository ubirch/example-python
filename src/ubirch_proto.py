import atexit
import logging
import pickle
from uuid import UUID

import ubirch

logger = logging.getLogger(__name__)


# the only part that is absolutely required for sending messages to ubirch here is the `_sign` method overload
# overloading `_verify` is required if you want to verify messages against your KeyStore
# we do some more stuff here to make re-running the demo a little bit nicer
class Proto(ubirch.Protocol):
    def __init__(self, key_store: ubirch.KeyStore, uuid: UUID) -> None:
        super().__init__()
        self.__ks = key_store
        self.load(uuid)
        logger.info("ubirch-protocol: device id: {}".format(uuid))
        atexit.register(self.persist, uuid)

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
        except:
            logger.warning("no existing saved signatures")
            pass

    def _sign(self, uuid: UUID, message: bytes) -> bytes:
        return self.__ks.find_signing_key(uuid).sign(message)

    def _verify(self, uuid: UUID, message: bytes, signature: bytes) -> None:
        return self.__ks.find_verifying_key(uuid).verify(signature, message)
