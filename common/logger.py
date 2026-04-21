import logging


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Create a simple structured logger for pipeline jobs."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(level.upper())
    return logger
