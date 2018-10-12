import time

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
        logger.info(reason)
        time.sleep(t)


def shorten(text):
    if len(text) > 50:
        return text[:22] + "..." + text[-25:]
    else:
        return text
