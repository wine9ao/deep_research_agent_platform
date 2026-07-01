"""
Structured logging setup for the Deep Research Agent Platform.

Provides a ``get_logger`` factory that returns a pre-configured logger with:
    - Timestamps in ISO-8601 format
    - Log level read from application settings
    - Module / name context
    - Console handler (coloured when available)
    - Optional rotating file handler

Usage::

    from app.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Agent started", extra={"iteration": 1})
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging import LogRecord

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_FMT = (
    "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)
DEFAULT_DATE_FMT = "%Y-%m-%dT%H:%M:%S"

_LOG_DIR = Path("logs")
_FILE_FMT = (
    "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(lineno)d | "
    "%(funcName)s | %(message)s"
)

_initialized: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_log_dir() -> Path:
    """Create the log directory if it does not exist and return its path."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _LOG_DIR


def _build_root_logger() -> logging.Logger:
    """
    Build and configure the root application logger.

    Adds a console handler and a rotating file handler.
    Ensures idempotency so multiple calls do not duplicate handlers.
    """
    global _initialized

    # Import here to avoid circular dependency at module-load time
    from app.utils.config import get_settings  # noqa: PLC0415

    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    root = logging.getLogger("deep_research")
    root.setLevel(level)

    if _initialized:
        return root

    # Prevent propagation to the Python root logger so we control formatting.
    root.propagate = False

    # --- Console handler --------------------------------------------------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(DEFAULT_FMT, datefmt=DEFAULT_DATE_FMT))

    # Attempt to add colour when the ``colorlog`` package is available.
    try:
        import colorlog  # noqa: PLC0415

        colour_fmt = (
            "%(log_color)s" + DEFAULT_FMT.replace("%(levelname)-8s", "%(levelname)-8s")
        )
        console_handler.setFormatter(
            colorlog.ColoredFormatter(
                colour_fmt,
                datefmt=DEFAULT_DATE_FMT,
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            )
        )
    except ImportError:
        pass

    root.addHandler(console_handler)

    # --- File handler -----------------------------------------------------
    _ensure_log_dir()
    file_handler = logging.FileHandler(_LOG_DIR / "app.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # always write debug+ to disk
    file_handler.setFormatter(logging.Formatter(_FILE_FMT, datefmt=DEFAULT_DATE_FMT))
    root.addHandler(file_handler)

    # --- Rotating file handler (optional) ---------------------------------
    try:
        from logging.handlers import RotatingFileHandler  # noqa: PLC0415

        rotating_handler = RotatingFileHandler(
            _LOG_DIR / "app.rotating.log",
            maxBytes=10 * 1024 * 1024,  # 10 MiB
            backupCount=5,
            encoding="utf-8",
        )
        rotating_handler.setLevel(logging.DEBUG)
        rotating_handler.setFormatter(
            logging.Formatter(_FILE_FMT, datefmt=DEFAULT_DATE_FMT)
        )
        root.addHandler(rotating_handler)
    except Exception:
        # RotatingFileHandler may fail in some restricted environments;
        # not critical — console + plain file are sufficient.
        pass

    _initialized = True
    return root


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a logger configured for the calling module.

    Args:
        name: Typically ``__name__`` from the calling module.  When omitted,
            the root platform logger is returned.

    Returns:
        A :class:`logging.Logger` instance with structured formatting.

    Example::

        logger = get_logger(__name__)
        logger.info("Starting research task", extra={"query_id": "abc"})
    """
    root = _build_root_logger()
    if name is None:
        return root
    return root.getChild(name)


def setup_logging() -> None:
    """
    Explicitly initialise the logging system.

    Calling this is optional — ``get_logger`` will lazy-initialise on first
    use.  Use this function when you need the logging infrastructure ready
    before the first log call (e.g., during application bootstrap).
    """
    _build_root_logger()
