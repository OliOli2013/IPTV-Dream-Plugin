# -*- coding: utf-8 -*-
"""IPTV Dream - Logger helpers (v6.2)

- Centralized logging to /tmp/iptvdream.log
- Optional debug mode
- Masking of sensitive credentials in logs

Designed to be safe on various Enigma2/Python images.
"""

from __future__ import absolute_import, print_function

import os
import re
import logging

try:
    from logging.handlers import RotatingFileHandler
except Exception:
    RotatingFileHandler = None

DEFAULT_LOG_FILE = "/tmp/iptvdream.log"
_MAX_BYTES = 512 * 1024
_BACKUP_COUNT = 2

# Mask common credential patterns (query params + JSON-ish)
_RE_QUERY = re.compile(r"([?&](?:password|pass|pwd)=)([^&]+)", re.IGNORECASE)
_RE_JSON  = re.compile(r"(\"(?:password|pass|pwd)\"\s*:\s*\")(.*?)(\")", re.IGNORECASE)
_RE_XTREAM_URL = re.compile(r"(username=)([^&]+)(&password=)([^&]+)", re.IGNORECASE)


def mask_sensitive(text):
    """Best-effort masking of credentials in strings."""
    try:
        if text is None:
            return ""
        s = str(text)
        s = _RE_QUERY.sub(r"\1***", s)
        s = _RE_JSON.sub(r"\1***\3", s)
        s = _RE_XTREAM_URL.sub(r"\1***\3***", s)
        return s
    except Exception:
        return "***"


def get_logger(name="IPTVDream", log_file=None, debug=False):
    """Return a configured logger singleton."""
    logger = logging.getLogger(name)
    level = logging.DEBUG if debug else logging.INFO

    # If already configured, just refresh level
    if getattr(logger, "_iptvdream_configured", False):
        logger.setLevel(level)
        for h in list(logger.handlers):
            try:
                h.setLevel(level)
            except Exception:
                pass
        return logger

    logger.setLevel(level)
    logger.propagate = False

    # Ensure a handler exists
    try:
        if log_file is None:
            log_file = DEFAULT_LOG_FILE

        # Guarantee directory exists
        try:
            d = os.path.dirname(log_file)
            if d:
                os.makedirs(d, exist_ok=True)
        except Exception:
            pass

        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        if RotatingFileHandler is not None:
            fh = RotatingFileHandler(log_file, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT)
        else:
            fh = logging.FileHandler(log_file)

        fh.setFormatter(fmt)
        fh.setLevel(level)
        logger.addHandler(fh)

    except Exception:
        # Last resort: stderr/basicConfig
        try:
            logging.basicConfig(level=level)
        except Exception:
            pass

    logger._iptvdream_configured = True
    return logger


def log_exception(logger, prefix, exc):
    try:
        logger.error("%s: %s", prefix, mask_sensitive(exc))
    except Exception:
        pass
