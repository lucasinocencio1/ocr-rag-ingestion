"""
Centralized loguru configuration for the application.
Import get_logger from here to use a consistent logger with module context.
"""
import os
import sys
from loguru import logger

from src.core.constants import APP_NAME


def _ensure_module(record: dict) -> bool:
    """Filter that sets default module so format never KeyErrors."""
    record["extra"].setdefault("module", APP_NAME)
    return True


def configure_logging(
    level: str | None = None,
    format: str | None = None,
) -> None:
    """
    Configure loguru: remove default handler and add one with app format/level.
    Called once at app startup; level can be overridden by LOG_LEVEL env.
    """
    logger.remove()
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_format = (
        format
        or "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[module]}</cyan> | <level>{message}</level>"
    )
    logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        filter=_ensure_module,
    )


def get_logger(module: str = APP_NAME):
    """
    Return a loguru logger bound to the given module name.
    Use in each module: logger = get_logger(__name__) or get_logger(APP_NAME).
    """
    return logger.bind(module=module)


__all__ = ["get_logger", "configure_logging", "logger"]
