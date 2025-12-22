# -*- coding: utf-8 -*-
"""IPTV Dream - Network helpers (v6.2)

Provides:
- timeouts (connect/read)
- retries with exponential backoff
- consistent error messages

This is a small wrapper around requests to reduce duplicated code.
"""

from __future__ import absolute_import, print_function

import time
import requests

from .logger import get_logger, mask_sensitive


class NetError(Exception):
    """Tagged network error with a short code."""

    def __init__(self, code, message):
        super(NetError, self).__init__("%s: %s" % (code, message))
        self.code = code
        self.message = message


def _default_timeout(timeout):
    # requests supports a (connect, read) tuple
    if timeout is None:
        return (7, 30)
    if isinstance(timeout, (int, float)):
        return (timeout, timeout)
    return timeout


def http_get(url, session=None, headers=None, timeout=None, retries=2, backoff=0.8,
            stream=False, verify=False, allow_redirects=True, debug=False, log_file=None):
    """HTTP GET with retries. Returns requests.Response."""
    logger = get_logger("IPTVDream.NET", log_file=log_file, debug=debug)
    timeout = _default_timeout(timeout)

    last_exc = None

    for attempt in range(0, max(0, int(retries)) + 1):
        try:
            if attempt > 0:
                sleep_s = backoff * (2 ** (attempt - 1))
                try:
                    time.sleep(sleep_s)
                except Exception:
                    pass

            s = session or requests
            logger.debug("GET %s (attempt %d/%d)", mask_sensitive(url), attempt + 1, int(retries) + 1)
            resp = s.get(
                url,
                headers=headers,
                timeout=timeout,
                stream=bool(stream),
                verify=bool(verify),
                allow_redirects=bool(allow_redirects),
            )

            # Raise on 4xx/5xx
            if resp.status_code >= 400:
                raise NetError("NET-HTTP-%d" % resp.status_code, "HTTP %d" % resp.status_code)

            return resp

        except NetError as e:
            # no point retrying on many 4xx, but we keep 429/5xx retryable
            last_exc = e
            retryable = False
            try:
                if str(e.code).startswith("NET-HTTP-"):
                    sc = int(str(e.code).split("-")[-1])
                    if sc in (408, 429) or sc >= 500:
                        retryable = True
            except Exception:
                pass

            logger.warning("%s for %s", e, mask_sensitive(url))
            if attempt >= int(retries) or not retryable:
                raise

        except requests.exceptions.Timeout as e:
            last_exc = e
            logger.warning("NET-TIMEOUT for %s", mask_sensitive(url))
            if attempt >= int(retries):
                raise NetError("NET-TIMEOUT", "Timeout")

        except requests.exceptions.RequestException as e:
            last_exc = e
            logger.warning("NET-REQUEST for %s (%s)", mask_sensitive(url), mask_sensitive(e))
            if attempt >= int(retries):
                raise NetError("NET-REQUEST", str(e))

        except Exception as e:
            last_exc = e
            logger.warning("NET-UNKNOWN for %s (%s)", mask_sensitive(url), mask_sensitive(e))
            if attempt >= int(retries):
                raise NetError("NET-UNKNOWN", str(e))

    # Should not reach
    raise NetError("NET-FAILED", str(last_exc) if last_exc else "Unknown")
