"""Application logger."""
import os
import logging

def get_logger(name: str, level: str = 'DEBUG'):
    """Return a configured logger."""
    level = os.environ.get('LOG_LEVEL') or level
    logger = logging.getLogger(name)
    logger.setLevel(level=level)
    return logger
