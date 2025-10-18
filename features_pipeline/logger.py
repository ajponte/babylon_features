"""Application logger."""

import os
import logging

DEFAULT_LOGGER_NAME = "features"


def get_logger(propagate: bool = False, level: str = "DEBUG"):
    """Return a configured logger."""

    handler = logging.StreamHandler()
    level = os.environ.get("LOG_LEVEL") or level
    logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    logger.propagate = propagate
    logger.setLevel(level=level)
    formatter = logging.Formatter(
        # pylint: disable=line-too-long
        fmt="[%(asctime)s.%(msecs)03d] %(levelname)s %(name)s:%(funcName)s: %(message)s",
        datefmt="%d/%b/%Y:%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
