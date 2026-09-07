# -*- coding: utf-8 -*-
"""IPTV Dream v8.0.1 - hardened network helpers.

The helper is intentionally small and defensive. It never touches Enigma2 UI
objects directly and every caller receives tagged errors that can be translated
into user-friendly messages.
"""
from __future__ import absolute_import, print_function

import time
import requests

from .logger import get_logger, mask_sensitive


class NetError(Exception):
    """Tagged network error with a short code and readable message."""

    def __init__(self, code, message, status_code=None, content_type=None):
        super(NetError, self).__init__("%s: %s" % (code, message))
        self.code = code
        self.message = message
        self.status_code = status_code
        self.content_type = content_type


DEFAULT_HEADERS = {
    # Do not look like python-requests. A lot of IPTV panels close such clients.
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'close',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}


def _default_timeout(timeout):
    if timeout is None:
        return (8, 90)
    if isinstance(timeout, (int, float)):
        return (timeout, timeout)
    return timeout


def _merge_headers(headers):
    out = dict(DEFAULT_HEADERS)
    try:
        for k, v in (headers or {}).items():
            if k and v is not None:
                out[str(k)] = str(v)
    except Exception:
        pass
    return out


def _response_snippet(resp, limit=220):
    try:
        raw = getattr(resp, 'content', b'') or b''
        if not raw:
            return ''
        txt = raw[:limit].decode('utf-8', 'ignore')
        txt = ' '.join(txt.replace('\r', ' ').replace('\n', ' ').split())
        return mask_sensitive(txt[:limit])
    except Exception:
        return ''


def response_info(resp):
    """Return compact status/content-type/body information for logs/errors."""
    try:
        sc = int(getattr(resp, 'status_code', 0) or 0)
    except Exception:
        sc = 0
    ct = ''
    loc = ''
    try:
        ct = resp.headers.get('content-type', '') or ''
        loc = resp.headers.get('location', '') or ''
    except Exception:
        pass
    parts = ["HTTP %d" % sc]
    if ct:
        parts.append("type=%s" % ct.split(';', 1)[0])
    if loc:
        parts.append("redirect=%s" % mask_sensitive(loc)[:120])
    snip = _response_snippet(resp)
    if snip:
        parts.append("body=%s" % snip)
    return '; '.join(parts)


def _is_retryable_http(code):
    try:
        sc = int(code)
    except Exception:
        return False
    return sc in (408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 530, 884) or sc >= 500


def _is_connection_abort(exc):
    s = str(exc).lower()
    needles = (
        'remotedisconnected', 'remote end closed connection', 'connection aborted',
        'connection reset', 'badstatusline', 'chunkedencodingerror', 'incompleteread',
        'connection broken', 'broken pipe'
    )
    return any(x in s for x in needles)


def http_get(url, session=None, headers=None, timeout=None, retries=2, backoff=0.8,
             stream=False, verify=False, allow_redirects=True, debug=False,
             log_file=None, allow_statuses=None, raise_for_status=True):
    """HTTP GET with bounded retries.

    Parameters kept backward-compatible with older IPTV Dream code.  v7 adds
    allow_statuses/raise_for_status so M3U loader can inspect unusual responses
    such as HTTP 884 before deciding if the body is really invalid.
    """
    logger = get_logger("IPTVDream.NET", log_file=log_file, debug=debug)
    timeout = _default_timeout(timeout)
    req_headers = _merge_headers(headers)
    allowed = set([int(x) for x in (allow_statuses or []) if str(x).isdigit()])

    last_exc = None
    total_attempts = max(0, int(retries)) + 1
    for attempt in range(total_attempts):
        try:
            if attempt > 0:
                try:
                    time.sleep(float(backoff) * (2 ** (attempt - 1)))
                except Exception:
                    pass

            s = session or requests
            logger.debug("GET %s (attempt %d/%d)", mask_sensitive(url), attempt + 1, total_attempts)
            resp = s.get(
                url,
                headers=req_headers,
                timeout=timeout,
                stream=bool(stream),
                verify=bool(verify),
                allow_redirects=bool(allow_redirects),
            )

            sc = int(getattr(resp, 'status_code', 0) or 0)
            if raise_for_status and sc >= 400 and sc not in allowed:
                raise NetError("NET-HTTP-%d" % sc, response_info(resp), sc, (resp.headers.get('content-type', '') if resp is not None else ''))
            return resp

        except NetError as e:
            last_exc = e
            logger.warning("%s for %s", e, mask_sensitive(url))
            retryable = _is_retryable_http(e.status_code or 0)
            if attempt >= int(retries) or not retryable:
                raise

        except requests.exceptions.Timeout:
            last_exc = NetError("NET-TIMEOUT", "Timeout")
            logger.warning("NET-TIMEOUT for %s", mask_sensitive(url))
            if attempt >= int(retries):
                raise last_exc

        except requests.exceptions.RequestException as e:
            code = "NET-ABORTED" if _is_connection_abort(e) else "NET-REQUEST"
            last_exc = NetError(code, str(e))
            logger.warning("%s for %s (%s)", code, mask_sensitive(url), mask_sensitive(e))
            if attempt >= int(retries):
                raise last_exc

        except Exception as e:
            code = "NET-ABORTED" if _is_connection_abort(e) else "NET-UNKNOWN"
            last_exc = NetError(code, str(e))
            logger.warning("%s for %s (%s)", code, mask_sensitive(url), mask_sensitive(e))
            if attempt >= int(retries):
                raise last_exc

    raise NetError("NET-FAILED", str(last_exc) if last_exc else "Unknown")
