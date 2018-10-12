import logging

logging.basicConfig(format='%(asctime)s %(name)20.20s %(levelname)-8.8s %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger("demo")
logger.setLevel(logging.INFO)

logging.getLogger("ubirch_client").setLevel(logging.INFO)
