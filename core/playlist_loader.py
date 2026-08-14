# -*- coding: utf-8 -*-
"""IPTV Dream v8.0.0 - robust playlist loader.

Rebuilt for provider compatibility:
- accepts valid M3U even when server sends wrong Content-Type (text/html),
- tries a small, deterministic set of headers similar to common IPTV tools,
- never loops endlessly,
- uses stale cache only as emergency fallback,
- parses M3U attributes safely with quoted commas and EXTGRP support.
"""
from __future__ import absolute_import, print_function

import os
import re
import time
import json
import gzip
import hashlib
import requests

try:
    from twisted.internet import reactor
except Exception:
    reactor = None

from .config_manager import ConfigManager
from ..tools.net import http_get, NetError, response_info, DEFAULT_HEADERS
from ..tools.logger import get_logger, mask_sensitive
from ..tools.channel_name_utils import clean_display_channel_name, clean_bouquet_name

CACHE_DIR = "/tmp/iptvdream_cache"
DEFAULT_CONFIG = "/etc/enigma2/iptvdream_v6_config.json"

UA_DESKTOP = DEFAULT_HEADERS.get('User-Agent')
UA_MAG = 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 4 rev: 1812 Mobile Safari/533.3'
UA_VLC = 'VLC/3.0.20 LibVLC/3.0.20'
UA_IPTV = 'Mozilla/5.0 IPTV-Dream/8.0.0 Enigma2'

HTML_MARKERS = (
    '<html', '<!doctype html', '<body', '<head', 'cloudflare', 'captcha',
    'access denied', 'forbidden', 'login', 'sign in', 'just a moment',
)


class PlaylistLoader(object):
    """M3U/Xtream playlist loading and parsing."""

    def __init__(self):
        self.config = ConfigManager(DEFAULT_CONFIG)
        self.cache_dir = CACHE_DIR
        self.session = requests.Session()
        self.debug = bool(self.config.get('debug', False))
        self.log_file = self.config.get('log_file', '/tmp/iptvdream.log')
        self.log = get_logger('IPTVDream.Playlist', log_file=self.log_file, debug=self.debug)
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception:
            pass

        self.session.headers.update(DEFAULT_HEADERS)
        try:
            ct = int(self.config.get('net_timeout_connect', 8))
        except Exception:
            ct = 8
        try:
            rt = int(self.config.get('net_timeout_read', 90))
        except Exception:
            rt = 90
        self.net_timeout = (max(3, ct), max(30, rt))
        self.net_retries = int(self.config.get('net_retries', 1))
        # Header variants are already retries. Do not multiply them into 8-12 HTTP attempts.
        self.m3u_variant_retries = max(0, int(self.config.get('m3u_variant_retries', 0)))
        self.net_backoff = float(self.config.get('net_backoff', 0.7))
        self.ssl_verify = bool(self.config.get('ssl_verify', False))

    # ---------- cache ----------
    def get_cache_key(self, value):
        return hashlib.md5((value or '').encode('utf-8', 'ignore')).hexdigest()

    def _cache_key_input(self, url, headers=None):
        parts = [url or '']
        try:
            for k in ('User-Agent', 'Referer', 'Origin'):
                v = (headers or {}).get(k)
                if v:
                    parts.append('%s=%s' % (k, v))
        except Exception:
            pass
        return '|'.join(parts)

    def _paths(self, url, headers=None):
        key = self.get_cache_key(self._cache_key_input(url, headers=headers))
        return key, os.path.join(self.cache_dir, key + '.m3u'), os.path.join(self.cache_dir, key + '.meta.json')

    def _read_meta_file(self, path):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _write_meta_file(self, path, meta):
        tmp = path + '.tmp'
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(meta or {}, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except Exception:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    def _read_cache(self, cache_file, max_age=None):
        try:
            if not cache_file or not os.path.exists(cache_file) or os.path.getsize(cache_file) <= 0:
                return None
            if max_age is not None and (time.time() - os.path.getmtime(cache_file)) > int(max_age):
                return None
            with open(cache_file, 'rb') as f:
                return f.read()
        except Exception:
            return None

    def is_cache_valid(self, cache_file, max_age=3600):
        return self._read_cache(cache_file, max_age=max_age) is not None

    def get_cached_content(self, url, headers=None):
        _key, cache_file, _meta = self._paths(url, headers=headers)
        return self._read_cache(cache_file, max_age=int(self.config.get('cache_max_age', 3600)))

    def get_cached_metadata(self, url, headers=None):
        _key, _cache, meta = self._paths(url, headers=headers)
        return self._read_meta_file(meta)

    def cache_content(self, url, content, meta=None, headers=None):
        _key, cache_file, meta_file = self._paths(url, headers=headers)
        tmp = cache_file + '.tmp'
        try:
            with open(tmp, 'wb') as f:
                f.write(content or b'')
            os.replace(tmp, cache_file)
            if meta:
                self._write_meta_file(meta_file, meta)
        except Exception:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    def _read_cache_file_any_age(self, cache_file):
        return self._read_cache(cache_file, max_age=None)

    def _meta_path(self, cache_key):
        return os.path.join(self.cache_dir, cache_key + '.meta.json')

    def _read_meta(self, cache_key):
        return self._read_meta_file(self._meta_path(cache_key))

    def _write_meta(self, cache_key, meta):
        return self._write_meta_file(self._meta_path(cache_key), meta)

    # ---------- content detection ----------
    def _decode_for_probe(self, data, limit=8192):
        try:
            if isinstance(data, (bytes, bytearray)):
                raw = data[:limit]
                if raw[:2] == b'\x1f\x8b':
                    try:
                        raw = gzip.decompress(data)[:limit]
                    except Exception:
                        pass
                return raw.decode('utf-8', 'ignore')
            return str(data or '')[:limit]
        except Exception:
            return ''

    def _maybe_decompress(self, data):
        try:
            if isinstance(data, (bytes, bytearray)) and data[:2] == b'\x1f\x8b':
                return gzip.decompress(data)
        except Exception:
            pass
        return data

    def _is_m3u_bytes(self, data):
        sample = self._decode_for_probe(data, limit=65536).lstrip('\ufeff\r\n\t ')
        low = sample.lower()
        if low.startswith('#extm3u'):
            return True
        # Some providers omit the first line but still return a valid list.
        return ('#extinf' in low and ('http://' in low or 'https://' in low or 'rtmp://' in low or 'rtsp://' in low))

    def _is_html_bytes(self, data):
        sample = self._decode_for_probe(data).lstrip('\ufeff\r\n\t ').lower()
        if not sample:
            return False
        if self._is_m3u_bytes(data):
            return False
        return any(x in sample for x in HTML_MARKERS)

    def _friendly_m3u_error(self, err, last_response=None):
        s = str(err or '')
        low = s.lower()
        if last_response is not None:
            try:
                info = response_info(last_response)
                sc = int(getattr(last_response, 'status_code', 0) or 0)
                ctype = (last_response.headers.get('content-type', '') or '').split(';', 1)[0]
                if sc == 884:
                    return ("Serwer zwrócił HTTP 884 (%s). To niestandardowa odpowiedź panelu IPTV: zwykle blokada IP, limit połączeń, "
                            "wymagany User-Agent/Referer albo link nie jest bezpośrednią playlistą M3U. %s" % (ctype or 'unknown type', info))
                if ctype == 'text/html' and self._is_html_bytes(last_response.content):
                    return "Serwer zwrócił stronę HTML zamiast listy M3U. Możliwa blokada, Cloudflare, login panel albo przekierowanie. %s" % info
            except Exception:
                pass
        if '884' in low:
            return "Serwer IPTV zwrócił HTTP 884. Sprawdź konto, blokadę IP, limit połączeń oraz wymagany User-Agent/Referer."
        if 'timeout' in low:
            return "Timeout podczas pobierania playlisty. Serwer odpowiada za wolno albo lista jest bardzo duża."
        if 'remote' in low or 'connection aborted' in low or 'connection reset' in low or 'net-aborted' in low:
            return "Serwer zamknął połączenie podczas pobierania playlisty. Możliwa blokada, przeciążony panel albo limit połączeń."
        if '401' in low or '403' in low:
            return "Serwer odrzucił autoryzację playlisty (401/403). Sprawdź login/hasło, ważność konta i blokadę IP."
        if '404' in low:
            return "Nie znaleziono playlisty (404). Link M3U jest błędny albo zmieniony przez dostawcę."
        return s[:240]

    def _header_variants(self, headers=None, url=''):
        variants = []
        base = dict(headers or {})
        if base:
            variants.append(base)
        # desktop/browser style
        variants.append({'User-Agent': UA_DESKTOP, 'Accept': '*/*', 'Connection': 'close'})
        # MAG/eStalker style, useful for providers reusing MAG guards for M3U too
        variants.append({'User-Agent': UA_MAG, 'Accept': '*/*', 'Connection': 'close'})
        # VLC style; many providers allow this when browsers are blocked
        variants.append({'User-Agent': UA_VLC, 'Accept': '*/*', 'Connection': 'close'})
        variants.append({'User-Agent': UA_IPTV, 'Accept': '*/*', 'Connection': 'close'})
        # Preserve Referer/Origin supplied by the user for every variant.
        out, seen = [], set()
        for h in variants:
            nh = dict(h)
            try:
                for k in ('Referer', 'Origin'):
                    if (headers or {}).get(k) and not nh.get(k):
                        nh[k] = headers.get(k)
            except Exception:
                pass
            sig = json.dumps(nh, sort_keys=True)
            if sig not in seen:
                seen.add(sig)
                out.append(nh)
        return out[:4]

    # ---------- download ----------
    def load_m3u_url(self, url, progress_callback=None, headers=None):
        """Download M3U with compatibility fallbacks.

        Returns raw bytes. The caller then parses them into channel dicts.
        """
        url = (url or '').strip()
        if not url:
            raise Exception('M3U load error: empty URL')
        cache_key, cache_file, meta_file = self._paths(url, headers=headers)

        def cb(pct, msg):
            try:
                if progress_callback:
                    if reactor:
                        reactor.callFromThread(progress_callback, int(pct), msg)
                    else:
                        progress_callback(int(pct), msg)
            except Exception:
                pass

        cached_fresh = self._read_cache(cache_file, max_age=int(self.config.get('cache_max_age', 3600)))
        cached_any = self._read_cache(cache_file, max_age=None)
        meta = self._read_meta_file(meta_file)
        last_exc = None
        last_resp = None

        header_variants = self._header_variants(headers=headers, url=url)
        for idx, h in enumerate(header_variants):
            try:
                pct = 5 + idx * 15
                cb(pct, 'Pobieranie M3U (%d/%d)' % (idx + 1, len(header_variants)))
                req_headers = dict(h)
                if cached_fresh:
                    try:
                        if meta.get('etag'):
                            req_headers['If-None-Match'] = meta.get('etag')
                        if meta.get('last_modified'):
                            req_headers['If-Modified-Since'] = meta.get('last_modified')
                    except Exception:
                        pass

                resp = http_get(
                    url,
                    session=self.session,
                    headers=req_headers,
                    stream=False,
                    verify=self.ssl_verify,
                    timeout=self.net_timeout,
                    retries=self.m3u_variant_retries,
                    backoff=self.net_backoff,
                    debug=self.debug,
                    log_file=self.log_file,
                    allow_statuses=[304, 400, 401, 403, 404, 429, 500, 502, 503, 504, 884],
                    raise_for_status=False,
                )
                last_resp = resp
                status = int(getattr(resp, 'status_code', 0) or 0)
                if status == 304 and cached_fresh:
                    cb(100, 'Z cache')
                    return cached_fresh

                content = self._maybe_decompress(resp.content or b'')
                if self._is_m3u_bytes(content):
                    self.cache_content(url, content, meta={
                        'url': url,
                        'saved_at': time.time(),
                        'size': len(content),
                        'etag': resp.headers.get('ETag', ''),
                        'last_modified': resp.headers.get('Last-Modified', ''),
                        'status_code': status,
                        'content_type': resp.headers.get('content-type', ''),
                    }, headers=headers)
                    cb(100, 'Gotowe')
                    return content

                # A wrong body is not immediately fatal: try next header variant.
                if status >= 400 or self._is_html_bytes(content):
                    last_exc = Exception(self._friendly_m3u_error('bad response', last_response=resp))
                    self.log.warning('M3U variant rejected: %s', mask_sensitive(last_exc))
                    continue

                # Unknown content. Some panels return plain text without #EXTM3U.
                text_probe = self._decode_for_probe(content, limit=2048).strip()
                if text_probe and ('://' in text_probe) and not self._is_html_bytes(content):
                    self.cache_content(url, content, headers=headers)
                    cb(100, 'Gotowe')
                    return content

                last_exc = Exception(self._friendly_m3u_error('empty or unsupported response', last_response=resp))
            except Exception as e:
                last_exc = e
                self.log.warning('M3U load attempt failed: %s', mask_sensitive(e))
                continue

        if cached_any:
            self.log.warning('M3U all attempts failed, using stale cache: %s', mask_sensitive(last_exc))
            cb(100, 'Stary cache')
            return cached_any
        raise Exception('M3U load error: %s' % self._friendly_m3u_error(last_exc, last_response=last_resp))

    def load_m3u_file(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            return self._maybe_decompress(data)
        except Exception as e:
            raise Exception('Błąd odczytu pliku: %s' % e)

    # ---------- parser ----------
    def _split_extinf(self, line):
        s = (line or '').strip()
        if not s.upper().startswith('#EXTINF:'):
            return '', ''
        s = s[len('#EXTINF:'):]
        in_q = False
        esc = False
        for i, ch in enumerate(s):
            if esc:
                esc = False
                continue
            if ch == '\\':
                esc = True
                continue
            if ch == '"':
                in_q = not in_q
            elif ch == ',' and not in_q:
                return s[:i], s[i + 1:]
        return s, ''

    def _parse_attrs(self, attrs):
        out = {}
        try:
            for m in re.finditer(r'([A-Za-z0-9_][A-Za-z0-9_\-]*)\s*=\s*"([^"]*)"', attrs or ''):
                out[(m.group(1) or '').strip().lower()] = (m.group(2) or '').strip()
            for m in re.finditer(r'([A-Za-z0-9_][A-Za-z0-9_\-]*)\s*=\s*([^\s,]+)', attrs or ''):
                k = (m.group(1) or '').strip().lower()
                if k not in out:
                    out[k] = (m.group(2) or '').strip().strip('"')
        except Exception:
            pass
        return out

    def _clean_title(self, value):
        v = (value or '').replace('\r', ' ').replace('\n', ' ').strip()
        v = re.sub(r'\s+', ' ', v)
        return v or 'No Name'

    def _kind_flags(self, title, group, url):
        text = ('%s %s %s' % (title or '', group or '', url or '')).lower()
        is_adult = bool(re.search(r'(^|[\s_\-\|/])(xxx|adult|porno|porn|erotic|sex|18\+|\+18)([\s_\-\|/]|$)', text))
        is_vod = ('/movie/' in text or '/series/' in text or bool(re.search(r'(^|[\s_\-\|/])(vod|movie|movies|film|films|serial|series)([\s_\-\|/]|$)', text)) or bool(re.search(r'\.(mp4|mkv|avi|mov|wmv|flv|m4v)(\?|$)', text)))
        return is_adult, is_vod

    def parse_m3u_content(self, content, progress_callback=None, content_filter=None):
        channels = []
        try:
            if isinstance(content, (bytes, bytearray)):
                text = self._maybe_decompress(content).decode('utf-8-sig', 'ignore')
            else:
                text = str(content or '')
        except Exception:
            text = str(content or '')

        current = {}
        pending_group = ''
        lines = text.splitlines()
        total = len(lines) or 1
        next_progress = 0

        def emit_progress(i):
            nonlocal next_progress
            if not progress_callback:
                return
            pct = int((float(i) / float(total)) * 100.0)
            if pct >= next_progress:
                next_progress += 10
                try:
                    if reactor:
                        reactor.callFromThread(progress_callback, min(99, pct), 'Parsowanie %d%%' % pct)
                    else:
                        progress_callback(min(99, pct), 'Parsowanie %d%%' % pct)
                except Exception:
                    pass

        for idx, raw in enumerate(lines):
            line = (raw or '').strip()
            if not line:
                continue
            if idx % 250 == 0:
                emit_progress(idx)
            low = line.lower()
            if low.startswith('#extinf'):
                attrs_raw, name_part = self._split_extinf(line)
                attrs = self._parse_attrs(attrs_raw)
                title = attrs.get('tvg-name') or attrs.get('name') or name_part or 'No Name'
                group = attrs.get('group-title') or attrs.get('group') or pending_group or 'Inne'
                logo = attrs.get('tvg-logo') or attrs.get('logo') or ''
                epg_id = attrs.get('tvg-id') or attrs.get('epg-id') or attrs.get('channel-id') or ''
                raw_title = self._clean_title(title)
                raw_group = self._clean_title(group)
                display_title = clean_display_channel_name(raw_title)
                display_group = clean_bouquet_name(raw_group)
                current = {
                    'title': display_title,
                    'name': display_title,
                    'group': display_group,
                    'raw_title': raw_title,
                    'raw_group': raw_group,
                    'logo': logo,
                    'tvg-logo': logo,
                    'epg_id': epg_id,
                    'tvg-id': epg_id,
                    'tvg-name': attrs.get('tvg-name') or '',
                    'catchup': attrs.get('catchup') or '',
                    'catchup-source': attrs.get('catchup-source') or '',
                    'timeshift': attrs.get('timeshift') or '',
                }
            elif low.startswith('#extgrp:'):
                raw_pending_group = self._clean_title(line.split(':', 1)[1])
                pending_group = clean_bouquet_name(raw_pending_group)
                if current:
                    current['raw_group'] = raw_pending_group
                    current['group'] = pending_group
            elif line.startswith('#'):
                continue
            elif '://' in line:
                url = line.strip()
                if not current:
                    current = {'title': 'Stream', 'name': 'Stream', 'group': pending_group or 'Inne', 'logo': '', 'tvg-logo': '', 'epg_id': '', 'tvg-id': ''}
                raw_title = current.get('raw_title') or current.get('title') or current.get('name') or 'No Name'
                raw_group = current.get('raw_group') or current.get('group') or 'Inne'
                title = clean_display_channel_name(raw_title)
                group = clean_bouquet_name(raw_group)
                current['title'] = title
                current['name'] = title
                current['group'] = group
                current.setdefault('raw_title', raw_title)
                current.setdefault('raw_group', raw_group)
                is_adult, is_vod = self._kind_flags(title, group, url)
                kind = 'adult' if is_adult else ('vod' if is_vod else 'live')
                if content_filter and content_filter not in ('all', kind):
                    if not (content_filter == 'live' and kind == 'live'):
                        current = {}
                        continue
                ch = dict(current)
                ch['url'] = url
                ch['title'] = self._clean_title(title)
                ch['name'] = ch['title']
                ch['group'] = self._clean_title(group)
                ch['is_adult'] = is_adult
                ch['is_vod'] = is_vod
                if kind == 'vod':
                    ch['type'] = 'vod'
                channels.append(ch)
                current = {}

        try:
            if progress_callback:
                if reactor:
                    reactor.callFromThread(progress_callback, 100, 'Gotowe')
                else:
                    progress_callback(100, 'Gotowe')
        except Exception:
            pass
        return channels

    def load_with_progress(self, source_type, source_data, progress_callback=None):
        if source_type == 'url':
            data = self.load_m3u_url(source_data, progress_callback=progress_callback)
            return self.parse_m3u_content(data, progress_callback=progress_callback)
        if source_type == 'file':
            data = self.load_m3u_file(source_data)
            return self.parse_m3u_content(data, progress_callback=progress_callback)
        raise Exception('Unsupported source type: %s' % source_type)

    def get_playlist_info(self, playlist):
        groups = {}
        adult = 0
        vod = 0
        for ch in playlist or []:
            g = ch.get('group') or 'Inne'
            groups[g] = groups.get(g, 0) + 1
            if ch.get('is_adult'):
                adult += 1
            if ch.get('is_vod'):
                vod += 1
        return {'total': len(playlist or []), 'groups': groups, 'adult': adult, 'vod': vod}

    def cleanup_cache(self, max_age=86400):
        removed = 0
        try:
            now = time.time()
            for fn in os.listdir(self.cache_dir):
                path = os.path.join(self.cache_dir, fn)
                if os.path.isfile(path) and now - os.path.getmtime(path) > int(max_age):
                    try:
                        os.remove(path); removed += 1
                    except Exception:
                        pass
        except Exception:
            pass
        return removed

    def get_performance_stats(self):
        return {'cache_dir': self.cache_dir, 'timeout': self.net_timeout, 'retries': self.net_retries}


class PlaylistCache(object):
    def __init__(self, cache_dir=CACHE_DIR):
        self.cache_dir = cache_dir
        self.index_file = os.path.join(cache_dir, 'index.json')
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:
            pass

    def load_index(self):
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def save_index(self, index):
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index or {}, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def add_to_cache(self, key, data):
        try:
            path = os.path.join(self.cache_dir, hashlib.md5(key.encode('utf-8', 'ignore')).hexdigest() + '.bin')
            with open(path, 'wb') as f:
                f.write(data if isinstance(data, (bytes, bytearray)) else str(data).encode('utf-8'))
            idx = self.load_index(); idx[key] = {'path': path, 'time': time.time()}; self.save_index(idx)
            return path
        except Exception:
            return None

    def get_from_cache(self, key, max_age=3600):
        idx = self.load_index()
        item = idx.get(key) or {}
        path = item.get('path')
        try:
            if path and os.path.exists(path) and time.time() - float(item.get('time', 0)) <= max_age:
                with open(path, 'rb') as f:
                    return f.read()
        except Exception:
            pass
        return None


class PerformanceMonitor(object):
    def __init__(self, stats_file='/tmp/iptvdream_stats.json'):
        self.stats_file = stats_file

    def load_stats(self):
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {'loads': []}

    def save_stats(self, stats):
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats or {}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def record_load(self, source, count, seconds):
        s = self.load_stats()
        s.setdefault('loads', []).append({'source': source, 'count': count, 'seconds': seconds, 'time': time.time()})
        s['loads'] = s.get('loads', [])[-50:]
        self.save_stats(s)

    def get_stats(self):
        return self.load_stats()
