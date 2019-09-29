import sys
import logging
from logging.handlers import RotatingFileHandler

import settings


# console handler
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(logging.Formatter(
    "[%(levelname)8s] [%(asctime)s] [%(name)s] %(message)s"))
logging.getLogger().addHandler(ch)

logger = logging.getLogger("server")  # pylint: disable=C0103
logger.setLevel(logging.getLevelName(settings.LOGGER_LEVEL))

# file handler
if settings.LOGGER_FILE:
    fh = RotatingFileHandler(
        settings.LOGGER_FILE, maxBytes=10 * 1024 * 1024, backupCount=100)
    fh.setFormatter(logging.Formatter(
        "[%(levelname)8s] [%(asctime)s] %(message)s"))
    logger.addHandler(fh)

logger.debug(
    "[] logger_level: %s logger_file: %s",
    settings.LOGGER_LEVEL, settings.LOGGER_FILE
)


__all__ = ["logger"]
