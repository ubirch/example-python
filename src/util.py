import struct
import time
from datetime import datetime, timezone, timedelta
from uuid import getnode

import colored
from colored import stylize
from halo import Halo

from config import add_stdout
from demo_logging import logger

ok = stylize("✔️ ", colored.fg("green"))
nok = stylize("❌ ", colored.fg("red"))
step = stylize("▶ ", colored.fg("blue"))


def abort():
    logger.error(stylize("Aborting!", colored.fg("red")))
    exit(1)


def wait(t, reason="Waiting..."):
    if add_stdout:
        with Halo(reason, spinner="dots"):
            time.sleep(t)
        logger.info(ok + reason + " done!")
    else:
        logger.info(step + reason)
        time.sleep(t)


def shorten(text):
    if len(text) > 50:
        return text[:22] + "..." + text[-25:]
    else:
        return text


def make_sensitive_message():
    now = datetime.now(timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)  # use POSIX epoch
    posix_timestamp_micros = (now - epoch) // timedelta(microseconds=1)
    posix_timestamp_millis = posix_timestamp_micros // 1000
    return struct.pack("LLf", getnode(), posix_timestamp_millis, 900)