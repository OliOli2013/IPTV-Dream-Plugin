# -*- coding: utf-8 -*-
"""IPTV Dream - Network helpers (v6.6.7 hotfix)

Provides:
- timeouts (connect/read)
- retries with exponential backoff
- safer headers for IPTV/M3U servers
- consistent and user-friendly network errors
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


DEFAULT_HEADERS = {
    # Some IPTV panels close connections when the client looks like python-requests.
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    # Keep-alive is a common reason for RemoteDisconnected on cheap panels/load balancers.
    'Connection': 'close',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}


def _default_timeout(timeout):
    # requests supports a (connect, read) tuple
    if timeout is None:
        return (10, 90)
    if isinstance(timeout, (int, float)):
        return (timeout, timeout)
    return timeout


def _merge_headers(headers):
    out = dict(DEFAULT_HEADERS)
    try:
        if headers:
            for k, v in headers.items():
                if k and v is not None:
                    out[str(k)] = str(v)
    except Exception:
        pass
    return out


def _response_snippet(resp, limit=180):
    try:
        raw = resp.content or b''
        if not raw:
            return ''
        txt = raw[:limit].decode('utf-8', 'ignore')
        txt = ' '.join(txt.replace('\r', ' ').replace('\n', ' ').split())
        return mask_sensitive(txt[:limit])
    except Exception:
        return ''


def _http_message(resp):
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
    # 884 is non-standard, but reported by some IPTV panels/load balancers.
    # A single retry with safe headers sometimes succeeds, otherwise the caller gets a clear error.
    return sc in (408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 530, 884) or sc >= 500


def _is_connection_abort(exc):
    s = str(exc).lower()
    needles = (
        'remotedisconnected',
        'remote end closed connection',
        'connection aborted',
        'connection reset',
        'badstatusline',
        'chunkedencodingerror',
        'incompleteread',
    )
    return any(x in s for x in needles)


def http_get(url, session=None, headers=None, timeout=None, retries=2, backoff=0.8,
             stream=False, verify=False, allow_redirects=True, debug=False, log_file=None):
    """HTTP GET with retries. Returns requests.Response."""
    logger = get_logger("IPTVDream.NET", log_file=log_file, debug=debug)
    timeout = _default_timeout(timeout)
    req_headers = _merge_headers(headers)

    last_exc = None
    total_attempts = max(0, int(retries)) + 1

    for attempt in range(0, total_attempts):
        try:
            if attempt > 0:
                sleep_s = float(backoff) * (2 ** (attempt - 1))
                try:
                    time.sleep(sleep_s)
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

            if resp.status_code >= 400:
                raise NetError("NET-HTTP-%d" % resp.status_code, _http_message(resp))

            return resp

        except NetError as e:
            last_exc = e
            retryable = False
            try:
                if str(e.code).startswith("NET-HTTP-"):
                    sc = int(str(e.code).split("-")[-1])
                    retryable = _is_retryable_http(sc)
            except Exception:
                retryable = False

            logger.warning("%s for %s", e, mask_sensitive(url))
            if attempt >= int(retries) or not retryable:
                raise

        except requests.exceptions.Timeout:
            last_exc = NetError("NET-TIMEOUT", "Timeout")
            logger.warning("NET-TIMEOUT for %s", mask_sensitive(url))
            if attempt >= int(retries):
                raise last_exc

        except requests.exceptions.RequestException as e:
            last_exc = e
            code = "NET-ABORTED" if _is_connection_abort(e) else "NET-REQUEST"
            logger.warning("%s for %s (%s)", code, mask_sensitive(url), mask_sensitive(e))
            if attempt >= int(retries):
                raise NetError(code, str(e))

        except Exception as e:
            last_exc = e
            code = "NET-ABORTED" if _is_connection_abort(e) else "NET-UNKNOWN"
            logger.warning("%s for %s (%s)", code, mask_sensitive(url), mask_sensitive(e))
            if attempt >= int(retries):
                raise NetError(code, str(e))

    raise NetError("NET-FAILED", str(last_exc) if last_exc else "Unknown")
