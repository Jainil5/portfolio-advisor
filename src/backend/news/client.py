"""Shared BSE access: polite calls with backoff, 403 handling, rotating logs."""

import logging
import os
import time
from logging.handlers import RotatingFileHandler

from bse import BSE

from backend.news import config

logger = logging.getLogger("backend.news")


class BSEBlocked(Exception):
    """BSE answered 403 - stop this run instead of hammering it."""


def setup_logging(level=logging.INFO):
    """Log to a rotating file in logs/ and to stderr (idempotent)."""
    if logger.handlers:
        return logger
    os.makedirs(config.LOG_DIR, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = RotatingFileHandler(config.LOG_FILE, maxBytes=2_000_000, backupCount=5)
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.setLevel(level)
    return logger


def attachment_url(attachment_name, pdf_flag=0):
    """BSE filing URL. PDFFLAG 0 -> AttachLive, 1 -> AttachHis (verified live)."""
    if not attachment_name:
        return ""
    folder = config.ATTACH_HIS if int(pdf_flag or 0) == 1 else config.ATTACH_LIVE
    return f"{config.ATTACHMENT_BASE}/{folder}/{attachment_name}"


def open_bse():
    """Context manager for a bse.BSE session."""
    os.makedirs(config.BSE_DOWNLOAD_DIR, exist_ok=True)
    return BSE(config.BSE_DOWNLOAD_DIR)


def call_with_retry(fn, *args, what="request", sleep=time.sleep, **kwargs):
    """Call a bse method, retrying timeouts/5xx with exponential backoff.

    Raises BSEBlocked on HTTP 403 (no retry) and ValueError unchanged
    (the library uses it for "not found").
    """
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except ValueError:
            raise
        except ConnectionError as exc:
            if str(exc).startswith("403"):
                logger.error("BSE returned 403 for %s - blocked; stopping this run.", what)
                raise BSEBlocked(str(exc)) from exc
            err = exc
        except (TimeoutError, OSError) as exc:
            err = exc
        if attempt == config.MAX_RETRIES:
            break
        wait = config.BACKOFF_BASE_S * 2 ** (attempt - 1)
        logger.warning("%s failed (%s); retry %d/%d in %.0fs",
                       what, err, attempt, config.MAX_RETRIES - 1, wait)
        sleep(wait)
    raise err
