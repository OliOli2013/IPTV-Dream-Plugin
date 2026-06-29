# -*- coding: utf-8 -*-
"""IPTV Dream v6.6.7 - MAC/Stalker/MAG helper.

Reworked after comparing mature IPTV plugins:
- fast, deterministic endpoint selection instead of probing many variants,
- MAG-like headers/cookies/session handling,
- bounded Stalker paging, no endless MAC loading,
- canonical MAC storage; deleted portals do not come back from .bak/legacy files.
"""
from __future__ import absolute_import, print_function

import json
import os
import random
import re
import string
import time

import requests

try:
    from urllib.parse import urlparse, urlencode, quote
except Exception:  # pragma: no cover - Py2 fallback if ever used
    from urlparse import urlparse  # type: ignore
    from urllib import urlencode, quote  # type: ignore

try:
    from Components.Language import language
except Exception:
    language = None

try:
    from .lang import _
except Exception:
    def _(txt, lang='pl'):
        return txt

try:
    from .logger import get_logger, mask_sensitive
except Exception:
    def get_logger(*a, **k):
        class L(object):
            def info(self, *a, **k): pass
            def warning(self, *a, **k): pass
            def error(self, *a, **k): pass
            def debug(self, *a, **k): pass
        return L()
    def mask_sensitive(x):
        return str(x)

MAC_FILE = "/etc/enigma2/iptvdream_mac.json"
LEGACY_MAC_FILES = ["/etc/enigma2/iptvdream_mylinks.json"]
LOG_MAC = get_logger("IPTVDream.MAC", log_file="/tmp/iptvdream.log", debug=False)

# Fast timeouts. Large VOD/series libraries still need time, but dead portals must not block the GUI forever.
MAC_CONNECT_TIMEOUT = 4
MAC_READ_TIMEOUT = 8
MAC_REQ_TIMEOUT = (MAC_CONNECT_TIMEOUT, MAC_READ_TIMEOUT)
MAC_SHORT_TIMEOUT = (3, 5)
MAC_MAX_LIVE_PAGES = 35
MAC_MAX_VOD_PAGES = 30
MAC_MAX_SERIES_PAGES = 20
MAC_MAX_ENDPOINTS = 5

JS_HTTPREQUEST = "1-xml"
MAG_UA = "Mozilla/5.0 (QtEmbedded; U; Linux; MAG250; en-US) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
MAG_XUA = "Model: MAG250; Link: Ethernet"
COMMON_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

_SESSION_CACHE = {}
_SESSION_TTL = 420

_MAC_HEX_RE = re.compile(r'[^0-9A-Fa-f]')
ADULT_RE = re.compile(
    r'(?i)(^|[\s\|_\-\[\]\(\):/])('
    r'xxx|adult|adults|porn|porno|pornhub|erotic|erotica|sex|sexy|hardcore|redlight|'
    r'hustler|brazzers|playboy|private|dorcel|babestation|venus|naughty|spice|blue\s*hustler|'
    r'18\+|\+18|for\s*adults|only\s*adults|dla\s*doroslych|dla\s*dorosłych'
    r')([\s\|_\-\[\]\(\):/]|$)'
)
ADULT_FALSE_RE = re.compile(r'(?i)\b(18\s*(lat|years|yo|roku|rok)|u18|under\s*18|18\s*hd|channel\s*18|canal\s*18)\b')


def _mask_mac(mac):
    try:
        m = (mac or "").replace(":", "").replace("-", "")
        if len(m) >= 6:
            return "**:**:**:**:%s:%s:%s" % (m[-6:-4], m[-4:-2], m[-2:])
    except Exception:
        pass
    return "****"


def normalize_mac(mac):
    raw = (mac or "").strip()
    cleaned = _MAC_HEX_RE.sub('', raw)
    if len(cleaned) != 12:
        return ''
    return ':'.join(cleaned[i:i + 2] for i in range(0, 12, 2)).lower()


def _ensure_scheme(u):
    u = (u or '').strip().replace('\\', '/')
    if not u:
        return u
    if not u.lower().startswith(('http://', 'https://')):
        u = 'http://' + u
    # compact duplicate slashes outside scheme
    tmp = u.replace('://', '§§')
    tmp = re.sub(r'/+', '/', tmp)
    return tmp.replace('§§', '://').rstrip('/')


def normalize_host(host):
    return _ensure_scheme(host)


def clean_name(name):
    if not name:
        return "No Name"
    name = str(name).strip()
    name = re.sub(r'^\[.*?\]\s*', '', name)
    name = re.sub(r'^\(.*?\)\s*', '', name)
    return name.strip() or "No Name"


def _is_adult_title_group(title, group=''):
    hay = ('%s %s' % (title or '', group or '')).strip().lower()
    if not hay:
        return False
    if ADULT_FALSE_RE.search(hay):
        return False
    return bool(ADULT_RE.search(' %s ' % hay))


def _is_adult_category_name(name):
    return _is_adult_title_group('', name)


def _lang():
    try:
        return (language.getLanguage()[:2] if language else 'pl') or 'pl'
    except Exception:
        return 'pl'


def translate_error(e, url=""):
    lang = _lang()
    err = str(e)
    low = err.lower()
    if 'invalid_mac' in low:
        return "Nieprawidłowy adres MAC lub host." if lang == 'pl' else "Invalid MAC address or host."
    if 'auth failed' in low or 'no token' in low:
        return ("Auth Failed. Portal nie zwrócił tokena. Sprawdź MAC, URL, /c/ i HTTP/HTTPS. Log: /tmp/iptvdream.log"
                if lang == 'pl' else
                "Auth Failed. Portal returned no token. Check MAC, URL, /c/ and HTTP/HTTPS. Log: /tmp/iptvdream.log")
    if 'bad_json_response' in low or 'expecting value' in low:
        return ("Portal zwrócił HTML/pustą odpowiedź zamiast JSON. Sprawdź adres, końcówkę /c/, port oraz HTTP/HTTPS."
                if lang == 'pl' else
                "Portal returned HTML/empty response instead of JSON. Check URL, /c/, port and HTTP/HTTPS.")
    if 'timeout' in low:
        return "Timeout połączenia z portalem." if lang == 'pl' else "Portal connection timeout."
    if '404' in err:
        return "Błąd 404 - zły adres portalu/endpoint." if lang == 'pl' else "404 error - wrong portal URL/endpoint."
    if '401' in err or '403' in err:
        return "Brak autoryzacji / blokada po stronie portalu." if lang == 'pl' else "Unauthorized / portal-side block."
    if 'remote' in low or 'connection aborted' in low or 'connection reset' in low:
        return "Portal zamknął połączenie. Możliwa blokada IP, zły port albo limit MAC." if lang == 'pl' else "Portal closed the connection. Possible IP block, wrong port or MAC limit."
    return ("Błąd MAC Portal: %s" if lang == 'pl' else "MAC Portal error: %s") % err[:160]


def _parse_json_flexible(raw_text):
    raw_text = (raw_text or '').strip()
    if not raw_text:
        return []
    try:
        return json.loads(raw_text)
    except Exception:
        pass
    items = []
    for line in raw_text.splitlines():
        line = line.strip().rstrip(',')
        if not line or line.startswith('#'):
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def _entry_host_value(entry):
    if not isinstance(entry, dict):
        return ''
    return entry.get('host') or entry.get('url') or entry.get('portal') or entry.get('portal_url') or ''


def _portal_name_from_host(host, fallback=''):
    candidate = (fallback or '').strip()
    if candidate:
        return candidate[:128]
    try:
        return (host.split('://', 1)[-1].split('/', 1)[0] or 'Portal')[:128]
    except Exception:
        return 'Portal'


def _normalize_portal_entry(entry):
    if not isinstance(entry, dict):
        return None
    host = normalize_host(_entry_host_value(entry))
    mac = normalize_mac(entry.get('mac') or entry.get('mac_address') or '')
    if not host or not mac:
        return None
    return {'name': _portal_name_from_host(host, entry.get('name') or entry.get('title') or ''), 'host': host, 'mac': mac}


def _items_from_mac_data(data):
    if data is None:
        return []
    if isinstance(data, dict):
        if _entry_host_value(data) and (data.get('mac') or data.get('mac_address')):
            return [data]
        if isinstance(data.get('portals'), list):
            return data.get('portals')
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict) and _entry_host_value(x) and (x.get('mac') or x.get('mac_address'))]
    return []


def _normalize_portal_list(data):
    data = _items_from_mac_data(data) if not isinstance(data, list) else data
    out, seen = [], set()
    for item in data or []:
        norm = _normalize_portal_entry(item)
        if not norm:
            continue
        key = '%s|%s' % (norm['host'].lower(), norm['mac'])
        if key in seen:
            continue
        seen.add(key)
        out.append(norm)
    return out


def _read_mac_json_file(path):
    try:
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return _parse_json_flexible(f.read())
    except Exception:
        return None


def load_mac_json():
    """Load canonical MAC list. Do not merge .bak when main file exists."""
    main_data = _read_mac_json_file(MAC_FILE)
    if main_data is not None:
        normalized = _normalize_portal_list(main_data)
        try:
            save_mac_json(normalized)
        except Exception:
            pass
        return normalized

    migrated = []
    for path in LEGACY_MAC_FILES + [MAC_FILE + '.bak'] + [x + '.bak' for x in LEGACY_MAC_FILES]:
        migrated.extend(_items_from_mac_data(_read_mac_json_file(path)))
    normalized = _normalize_portal_list(migrated)
    if normalized:
        try:
            save_mac_json(normalized)
        except Exception:
            pass
    return normalized


def save_mac_json(data):
    data = _normalize_portal_list(data)
    base_dir = os.path.dirname(MAC_FILE)
    try:
        if base_dir and not os.path.exists(base_dir):
            os.makedirs(base_dir)
    except Exception:
        pass
    tmp = MAC_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        try:
            f.flush(); os.fsync(f.fileno())
        except Exception:
            pass
    try:
        os.replace(tmp, MAC_FILE)
    except Exception:
        if os.path.exists(MAC_FILE):
            try: os.remove(MAC_FILE)
            except Exception: pass
        os.rename(tmp, MAC_FILE)
    # .bak mirrors current state only; empty list means remove backups.
    try:
        bak = MAC_FILE + '.bak'
        if data:
            import shutil
            shutil.copy2(MAC_FILE, bak)
        elif os.path.exists(bak):
            os.remove(bak)
    except Exception:
        pass


def clear_mac_backups():
    for path in [MAC_FILE + '.bak'] + [x + '.bak' for x in LEGACY_MAC_FILES]:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def add_mac_portal(host, mac, name=None):
    entry = _normalize_portal_entry({'host': host, 'mac': mac, 'name': name})
    if not entry:
        raise ValueError('INVALID_MAC_OR_HOST')
    portals = load_mac_json()
    key = '%s|%s' % (entry['host'].lower(), entry['mac'])
    for idx, p in enumerate(portals):
        if '%s|%s' % ((p.get('host') or '').lower(), p.get('mac') or '') == key:
            portals[idx] = entry
            save_mac_json(portals)
            return entry
    portals.append(entry)
    save_mac_json(portals)
    return entry


def get_random_sn():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(13))


def _read_local_timezone():
    try:
        if os.path.exists('/etc/timezone'):
            tz = open('/etc/timezone').read().strip()
            if tz and '/' in tz and not tz.startswith('#'):
                return tz
    except Exception:
        pass
    return 'Europe/London'


def _base_url_and_path(host):
    u = _ensure_scheme(host)
    p = urlparse(u)
    base = '%s://%s' % (p.scheme or 'http', p.netloc)
    path = (p.path or '').strip('/')
    return base.rstrip('/'), path.rstrip('/')


def _dedupe(seq):
    out, seen = [], set()
    for x in seq:
        x = (x or '').strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _make_endpoints(host):
    base, path = _base_url_and_path(host)
    endpoints = []
    u = _ensure_scheme(host)
    low = path.lower()
    if low.endswith('server/load.php') or low.endswith('portal.php') or low.endswith('load.php'):
        endpoints.append(u)
    else:
        # Keep user hint first. This is what avoids slow endpoint probing.
        if low.endswith('/c') or low == 'c':
            root = path[:-2].rstrip('/')
            prefix = ('/' + root) if root else ''
            endpoints.append(base + prefix + '/server/load.php')
            endpoints.append(base + prefix + '/c/portal.php')
            endpoints.append(base + prefix + '/c/server/load.php')
        elif low:
            prefix = '/' + path
            endpoints.append(base + prefix + '/server/load.php')
            endpoints.append(base + prefix + '/c/portal.php')
            endpoints.append(base + prefix + '/portal.php')
        else:
            # Common defaults used by Stalker/MAG/eStalker-like plugins.
            endpoints.append(base + '/server/load.php')
            endpoints.append(base + '/c/portal.php')
            endpoints.append(base + '/c/server/load.php')
            endpoints.append(base + '/stalker_portal/server/load.php')
            endpoints.append(base + '/stalker_portal/c/portal.php')
    # portal.php/load.php alternative pairs, de-duplicated and capped.
    extra = []
    for ep in endpoints:
        if ep.endswith('/server/load.php'):
            extra.append(ep[:-len('/server/load.php')] + '/c/portal.php')
        if ep.endswith('/c/portal.php'):
            root = ep[:-len('/c/portal.php')]
            extra.append(root + '/server/load.php')
    return _dedupe(endpoints + extra)[:MAC_MAX_ENDPOINTS]


def _referer_for_endpoint(endpoint):
    try:
        p = urlparse(endpoint)
        base = '%s://%s' % (p.scheme, p.netloc)
        path = p.path or ''
        if '/stalker_portal/' in path:
            return base + '/stalker_portal/c/'
        if '/portal/' in path:
            return base + '/portal/c/'
        if '/mag/' in path:
            return base + '/mag/c/'
        if path.endswith('/c/portal.php') or '/c/server/' in path:
            return base + '/c/'
        pref = path.rsplit('/server/load.php', 1)[0]
        if pref:
            return base + pref + '/c/'
        return base + '/c/'
    except Exception:
        return ''


def _portal_root_from_endpoint(endpoint):
    try:
        p = urlparse(endpoint)
        base = '%s://%s' % (p.scheme, p.netloc)
        path = p.path or ''
        for suffix in ('/server/load.php', '/c/portal.php', '/portal.php', '/load.php'):
            if path.endswith(suffix):
                root = path[:-len(suffix)].rstrip('/')
                if root.endswith('/c'):
                    root = root[:-2].rstrip('/')
                return (base + root).rstrip('/')
    except Exception:
        pass
    return _base_url_and_path(endpoint)[0]


def _origin(referer):
    try:
        p = urlparse(referer)
        if p.scheme and p.netloc:
            return '%s://%s' % (p.scheme, p.netloc)
    except Exception:
        pass
    return ''


def _headers(mac, referer=''):
    tz = quote(_read_local_timezone())
    h = {
        'User-Agent': MAG_UA,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-User-Agent': MAG_XUA,
        'Connection': 'keep-alive',
        'Cookie': 'mac=%s; stb_lang=en; timezone=%s' % (mac, tz),
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }
    if referer:
        h['Referer'] = referer
        o = _origin(referer)
        if o:
            h['Origin'] = o
    return h


def _looks_json(txt):
    t = (txt or '').lstrip()
    return t.startswith('{') or t.startswith('[')


def _json_from_response(resp):
    try:
        return resp.json()
    except Exception:
        txt = ''
        try:
            txt = resp.text or ''
        except Exception:
            txt = ''
        if not txt or not _looks_json(txt):
            raise Exception('BAD_JSON_RESPONSE')
        return json.loads(txt)


def _unwrap_js(data):
    if isinstance(data, dict) and 'js' in data:
        js = data.get('js')
        if isinstance(js, str):
            st = js.strip()
            if st.startswith('{') or st.startswith('['):
                try:
                    return json.loads(st)
                except Exception:
                    return js
        return js
    return data


def _data_list(obj):
    obj = _unwrap_js(obj)
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ('data', 'items', 'channels', 'list'):
            v = obj.get(k)
            if isinstance(v, list):
                return v
    return []


def _extract_token(data):
    js = _unwrap_js(data)
    if isinstance(js, dict):
        tok = js.get('token') or js.get('access_token')
        rnd = js.get('random') or ''
        if not tok and isinstance(js.get('data'), dict):
            tok = js.get('data', {}).get('token')
            rnd = js.get('data', {}).get('random') or rnd
        return (tok or '').strip(), (rnd or '').strip()
    if isinstance(data, dict):
        return (data.get('token') or '').strip(), (data.get('random') or '').strip()
    return '', ''


class StalkerClient(object):
    def __init__(self, host, mac):
        self.host = normalize_host(host)
        self.mac = normalize_mac(mac)
        if not self.host or not self.mac:
            raise Exception('INVALID_MAC')
        self.session = requests.Session()
        self.session.verify = False
        self.endpoints = _make_endpoints(self.host)
        self.endpoint = ''
        self.referer = ''
        self.token = ''
        self.token_random = ''
        self.portal_root = _base_url_and_path(self.host)[0]

    def _warmup(self, referer):
        if not referer:
            return referer
        try:
            r = self.session.get(referer, headers=_headers(self.mac, referer), timeout=MAC_SHORT_TIMEOUT, verify=False, allow_redirects=True)
            return getattr(r, 'url', None) or referer
        except Exception:
            return referer

    def _request(self, endpoint, params, headers=None, timeout=MAC_REQ_TIMEOUT, post=False):
        h = dict(headers or _headers(self.mac, self.referer))
        if self.token:
            h['Authorization'] = 'Bearer ' + self.token
        try:
            if post:
                r = self.session.post(endpoint, params=params, data='', headers=h, timeout=timeout, verify=False, allow_redirects=True)
            else:
                r = self.session.get(endpoint, params=params, headers=h, timeout=timeout, verify=False, allow_redirects=True)
            r.raise_for_status()
            return _json_from_response(r)
        except Exception:
            raise

    def _call_at(self, endpoint, type_, action, extra=None, allow_post=False):
        base = {'type': type_, 'action': action, 'JsHttpRequest': JS_HTTPREQUEST}
        if extra:
            base.update(extra)
        last = None
        variants = [base]
        # Some panels accept the same API only without JsHttpRequest. Keep this as a small fallback.
        nojs = dict(base); nojs.pop('JsHttpRequest', None)
        variants.append(nojs)
        for params in variants:
            try:
                return self._request(endpoint, params, timeout=MAC_REQ_TIMEOUT, post=False)
            except Exception as e:
                last = e
            if allow_post:
                try:
                    return self._request(endpoint, params, timeout=MAC_REQ_TIMEOUT, post=True)
                except Exception as e:
                    last = e
        if last:
            raise last
        raise Exception('BAD_JSON_RESPONSE')

    def call(self, type_, action, extra=None, allow_post=False):
        if not self.endpoint:
            raise Exception('Auth Failed')
        return self._call_at(self.endpoint, type_, action, extra=extra, allow_post=allow_post)

    def handshake(self):
        # Reuse session within one Enigma process to speed refreshing same portal.
        key = '%s|%s' % (self.host.rstrip('/').lower(), self.mac)
        now = time.time()
        cached = _SESSION_CACHE.get(key)
        if cached and now - cached.get('ts', 0) < _SESSION_TTL:
            try:
                self.session = cached['session']
                self.endpoint = cached['endpoint']
                self.referer = cached['referer']
                self.token = cached['token']
                self.token_random = cached.get('random', '')
                self.portal_root = cached.get('portal_root') or _portal_root_from_endpoint(self.endpoint)
                return self.token
            except Exception:
                pass

        last = None
        for ep in self.endpoints:
            self.endpoint = ep
            self.referer = self._warmup(_referer_for_endpoint(ep))
            self.portal_root = _portal_root_from_endpoint(ep)
            try:
                LOG_MAC.info('handshake endpoint=%s referer=%s mac=%s', ep, self.referer, _mask_mac(self.mac))
            except Exception:
                pass
            for extra in ({'token': ''}, {}, {'mac': self.mac, 'token': ''}):
                try:
                    data = self._call_at(ep, 'stb', 'handshake', extra=extra, allow_post=True)
                    token, rnd = _extract_token(data)
                    if token:
                        self.token = token
                        self.token_random = rnd
                        _SESSION_CACHE[key] = {
                            'session': self.session, 'endpoint': self.endpoint, 'referer': self.referer,
                            'token': self.token, 'random': self.token_random, 'portal_root': self.portal_root, 'ts': time.time()
                        }
                        try:
                            self.get_profile()
                        except Exception:
                            pass
                        return token
                except Exception as e:
                    last = e
                    continue
        try:
            LOG_MAC.error('Auth Failed host=%s mac=%s last=%s', self.host, _mask_mac(self.mac), mask_sensitive(last))
        except Exception:
            pass
        raise Exception('Auth Failed')

    def get_profile(self):
        params = {'hd': '1', 'ver': 'ImageDescription: 0.2.18-r14-pub-250; API Version: JS API version: 328; STB API version: 134;', 'num_banks': '2', 'stb_type': 'MAG250', 'client_type': 'STB'}
        return self.call('stb', 'get_profile', params, allow_post=False)

    def get_genres(self, kind='itv'):
        action = 'get_genres' if kind == 'itv' else 'get_categories'
        return _data_list(self.call(kind, action, {}, allow_post=False))

    def get_all_channels(self):
        return _data_list(self.call('itv', 'get_all_channels', {}, allow_post=False))

    def ordered_list(self, kind='itv', category_id='', max_pages=30, sortby='number'):
        params_names = ['genre', 'category', 'genre_id', 'category_id', 'tv_genre_id'] if category_id not in (None, '', '*') else ['']
        best = []
        for pname in params_names:
            rows = self._ordered_list_one(kind, pname, category_id, max_pages=max_pages, sortby=sortby)
            if rows:
                return rows
            if len(rows) > len(best):
                best = rows
        return best

    def _ordered_list_one(self, kind, param_name, category_id, max_pages=30, sortby='number'):
        seen, out, no_progress = set(), [], 0
        first_nonempty_page = None
        for page in range(int(max_pages)):
            page_no = page if first_nonempty_page is not None else page
            params = {'fav': '0', 'sortby': sortby, 'p': str(page_no)}
            if param_name and category_id not in (None, '', '*'):
                params[param_name] = str(category_id)
            try:
                data = self.call(kind, 'get_ordered_list', params, allow_post=False)
            except Exception:
                # If p=0 failed empty/exception on first page, try p=1 once.
                if page == 0:
                    try:
                        params['p'] = '1'
                        data = self.call(kind, 'get_ordered_list', params, allow_post=False)
                    except Exception:
                        break
                else:
                    break
            rows = _data_list(data)
            if not rows:
                if page == 0:
                    try:
                        params['p'] = '1'
                        data = self.call(kind, 'get_ordered_list', params, allow_post=False)
                        rows = _data_list(data)
                    except Exception:
                        rows = []
                if not rows:
                    break
            first_nonempty_page = page
            added = 0
            for it in rows:
                if not isinstance(it, dict):
                    continue
                iid = str(it.get('id') or it.get('ch_id') or it.get('movie_id') or it.get('series_id') or it.get('name') or it.get('title') or '')
                cmd = str(it.get('cmd') or it.get('play_cmd') or it.get('command') or '')
                key = iid + '|' + cmd
                if key in seen:
                    continue
                seen.add(key); out.append(it); added += 1
            no_progress = no_progress + 1 if added == 0 else 0
            if no_progress >= 2 or len(rows) < 10:
                break
        return out

    @staticmethod
    def clean_cmd(cmd):
        c = str(cmd or '').strip()
        c = re.sub(r'^(ffmpeg|auto|ffrt)\s+', '', c, flags=re.I).strip()
        if (c.startswith('"') and c.endswith('"')) or (c.startswith("'") and c.endswith("'")):
            c = c[1:-1].strip()
        return c

    def link(self, cmd, kind='itv'):
        cmd_clean = self.clean_cmd(cmd)
        if not cmd_clean:
            return ''
        for action in ('create_link', 'get_link'):
            try:
                data = self.call(kind, action, {'cmd': cmd_clean}, allow_post=False)
                js = _unwrap_js(data)
                link = ''
                if isinstance(js, dict):
                    link = js.get('cmd') or js.get('url') or js.get('data') or ''
                    if isinstance(link, dict):
                        link = link.get('cmd') or link.get('url') or ''
                elif isinstance(js, str):
                    link = js
                link = self.clean_cmd(link)
                if link:
                    return link
            except Exception:
                continue
        return ''


def _client(host, mac):
    c = StalkerClient(host, mac)
    c.handshake()
    return c


def _row_gid(row):
    if not isinstance(row, dict):
        return ''
    for key in ('tv_genre_id', 'genre_id', 'category_id', 'category', 'genre', 'tv_genre', 'group_id'):
        v = row.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ''


def _group_matches(row, gid):
    gid = str(gid or '').strip()
    if not gid:
        return True
    vals = []
    for key in ('tv_genre_id', 'genre_id', 'category_id', 'category', 'genre', 'tv_genre', 'group_id'):
        vals.append(str(row.get(key) or '').strip())
    return (gid in vals) if any(vals) else True


def _is_local_url(url):
    u = (url or '').strip().lower()
    return u.startswith(('http://localhost/', 'https://localhost/', 'http://127.0.0.1/', 'https://127.0.0.1/')) or '/localhost/' in u


def _abs_logo(logo, root):
    logo = str(logo or '').strip()
    if logo and not logo.startswith(('http://', 'https://')):
        return root.rstrip('/') + '/' + logo.lstrip('/')
    return logo


def _play_url(client, row, kind='itv', resolve=True):
    cmd = row.get('cmd') or row.get('play_cmd') or row.get('command') or row.get('cmds') or ''
    direct = StalkerClient.clean_cmd(cmd)
    if direct.startswith(('http://', 'https://', 'rtmp://', 'rtsp://')) and not _is_local_url(direct):
        # Keep direct URLs; resolving all channels would slow down big portals.
        return direct
    if resolve:
        try:
            u = client.link(cmd, kind)
            if u and not _is_local_url(u):
                return u
        except Exception:
            pass
    url = str(row.get('url') or '').strip()
    if url and not _is_local_url(url):
        return url
    # Last lightweight fallback used by some portals. Better to return something than block forever.
    cid = row.get('id') or row.get('ch_id') or row.get('number') or ''
    if cid:
        return client.portal_root.rstrip('/') + '/mpegts_to_ts/' + str(cid)
    return ''


def _channel_from_live(client, row, genres, forced_group=None, resolve=True):
    name = clean_name(row.get('name') or row.get('title') or ('Channel %s' % (row.get('id') or '')))
    gid = _row_gid(row)
    group = forced_group or genres.get(gid) or row.get('genre') or row.get('category') or row.get('tv_genre') or 'Inne'
    group = clean_name(group)
    adult = _is_adult_title_group(name, group)
    if adult:
        group = 'XXX'
    logo = _abs_logo(row.get('logo') or row.get('icon') or row.get('stream_icon') or row.get('screenshot_uri') or '', client.portal_root)
    url = _play_url(client, row, 'itv', resolve=resolve)
    return {
        'title': name,
        'url': url,
        'group': group,
        'logo': logo,
        'tvg-logo': logo,
        'epg': '',
        'epg_id': str(row.get('xmltv_id') or row.get('tvg_id') or row.get('epg_id') or row.get('epg_channel_id') or ''),
        'is_adult': adult,
        'channel_id': str(row.get('id') or row.get('ch_id') or '')
    }


def _fetch_m3u_shortcut(host, mac):
    # Optional fast path used by some panels. It is intentionally short-timeout and best-effort only.
    try:
        base, _path = _base_url_and_path(host)
        url = '%s/get.php?username=%s&password=%s&type=m3u_plus&output=ts' % (base, mac, mac)
        r = requests.get(url, headers={'User-Agent': COMMON_UA, 'Connection': 'close'}, timeout=(3, 7), verify=False, allow_redirects=True)
        if r.status_code == 200 and '#EXTINF' in (r.text or ''):
            return parse_m3u_text(r.text)
    except Exception:
        pass
    return []


def parse_mac_playlist(host, mac, content_type='live', progress_callback=None):
    host = normalize_host(host)
    mac = normalize_mac(mac)
    if not host or not mac:
        raise Exception('INVALID_MAC')

    def cb(p, msg=''):
        try:
            if progress_callback:
                progress_callback(int(p), msg or '')
        except Exception:
            pass

    try:
        LOG_MAC.info('MAC start type=%s host=%s mac=%s', content_type, host, _mask_mac(mac))
    except Exception:
        pass

    try:
        # M3U shortcut first for LIVE/ADULT only. If it fails, do real MAG/Stalker.
        if content_type in ('live', 'adult'):
            cb(2, 'M3U shortcut')
            quick = _fetch_m3u_shortcut(host, mac)
            if quick:
                if content_type == 'adult':
                    quick = [x for x in quick if _is_adult_title_group(x.get('title') or x.get('name'), x.get('group'))]
                else:
                    quick = [x for x in quick if not _is_adult_title_group(x.get('title') or x.get('name'), x.get('group'))]
                cb(100, 'OK')
                return quick

        cb(4, 'Handshake')
        client = _client(host, mac)

        if content_type in ('live', 'adult'):
            cb(8, 'Genres')
            genres = {}
            genre_order = []
            adult_ids = []
            try:
                for g in client.get_genres('itv') or []:
                    if not isinstance(g, dict):
                        continue
                    gid = str(g.get('id') or g.get('genre_id') or g.get('category_id') or '').strip()
                    name = clean_name(g.get('title') or g.get('name') or 'Inne')
                    if gid:
                        genres[gid] = name
                        genre_order.append(gid)
                        if _is_adult_category_name(name):
                            adult_ids.append(gid)
                    alias = str(g.get('alias') or '').strip()
                    if alias:
                        genres[alias] = name
            except Exception:
                pass

            rows = []
            if content_type == 'live':
                cb(15, 'All channels')
                try:
                    rows = client.get_all_channels() or []
                except Exception as e:
                    try: LOG_MAC.info('get_all_channels failed: %s', mask_sensitive(e))
                    except Exception: pass
                    rows = []

            out = []
            seen = set()
            if rows:
                total = len(rows) or 1
                # Resolve local/non-direct links only when list is not enormous. Huge lists must load first.
                resolve = total <= 400
                for i, row in enumerate(rows):
                    if not isinstance(row, dict):
                        continue
                    if i % 80 == 0:
                        cb(15 + int((i / float(total)) * 80), 'LIVE %d/%d' % (i, total))
                    ch = _channel_from_live(client, row, genres, resolve=resolve)
                    if not ch.get('url'):
                        continue
                    if content_type == 'adult' and not ch.get('is_adult'):
                        continue
                    if content_type == 'live' and ch.get('is_adult'):
                        continue
                    key = (ch.get('channel_id') or '') + '|' + (ch.get('url') or '') + '|' + ch.get('title','')
                    if key in seen:
                        continue
                    seen.add(key); out.append(ch)
                cb(100, 'OK')
                return out

            # Fallback like IPTV bouquets generators: ordered_list per real genre, not alias loops.
            cats = adult_ids if content_type == 'adult' and adult_ids else list(genre_order)
            if not cats:
                cats = ['']
            total_cats = len(cats) or 1
            for cidx, gid in enumerate(cats):
                gname = genres.get(str(gid), 'XXX' if content_type == 'adult' else 'Inne')
                cb(15 + int((cidx / float(total_cats)) * 80), 'LIVE: %s' % gname)
                try:
                    cat_rows = client.ordered_list('itv', gid, max_pages=MAC_MAX_LIVE_PAGES, sortby='number')
                except Exception:
                    cat_rows = []
                resolve = len(cat_rows) <= 350
                for row in cat_rows:
                    if not isinstance(row, dict):
                        continue
                    if gid and not _group_matches(row, gid):
                        continue
                    ch = _channel_from_live(client, row, genres, forced_group=gname if gid else None, resolve=resolve)
                    if not ch.get('url'):
                        continue
                    if content_type == 'adult' and not (ch.get('is_adult') or _is_adult_category_name(gname)):
                        continue
                    if content_type == 'live' and ch.get('is_adult'):
                        continue
                    key = (ch.get('channel_id') or '') + '|' + (ch.get('url') or '') + '|' + ch.get('title','')
                    if key in seen:
                        continue
                    seen.add(key); out.append(ch)
            if out:
                cb(100, 'OK')
                return out
            raise Exception('Empty List')

        if content_type == 'vod':
            cb(8, 'VOD categories')
            cats = client.get_genres('vod') or []
            out = []
            total_cats = len(cats) or 1
            for cidx, cat in enumerate(cats):
                if not isinstance(cat, dict):
                    continue
                cid = cat.get('id') or cat.get('category_id')
                if cid is None:
                    continue
                group = clean_name(cat.get('title') or cat.get('name') or 'VOD')
                cb(10 + int((cidx / float(total_cats)) * 85), 'VOD: %s' % group)
                for it in client.ordered_list('vod', cid, max_pages=MAC_MAX_VOD_PAGES, sortby='added'):
                    if not isinstance(it, dict):
                        continue
                    title = clean_name(it.get('name') or it.get('title') or 'VOD')
                    logo = _abs_logo(it.get('screenshot_uri') or it.get('poster') or it.get('cover') or it.get('logo') or '', client.portal_root)
                    cmd = it.get('cmd') or it.get('play_cmd') or it.get('command') or ''
                    url = client.link(cmd, 'vod') or StalkerClient.clean_cmd(cmd)
                    if not url:
                        continue
                    out.append({'title': title, 'url': url, 'group': group, 'logo': logo, 'tvg-logo': logo, 'epg': '', 'is_vod': True})
            cb(100, 'OK')
            return out

        if content_type == 'series':
            cb(8, 'Series categories')
            cats = client.get_genres('series') or []
            out = []
            total_cats = len(cats) or 1
            for cidx, cat in enumerate(cats):
                if not isinstance(cat, dict):
                    continue
                cid = cat.get('id') or cat.get('category_id')
                if cid is None:
                    continue
                group = clean_name(cat.get('title') or cat.get('name') or 'Series')
                cb(10 + int((cidx / float(total_cats)) * 85), 'SERIES: %s' % group)
                for it in client.ordered_list('series', cid, max_pages=MAC_MAX_SERIES_PAGES, sortby='added'):
                    if not isinstance(it, dict):
                        continue
                    title = clean_name(it.get('name') or it.get('title') or 'Series')
                    logo = _abs_logo(it.get('screenshot_uri') or it.get('poster') or it.get('cover') or it.get('logo') or '', client.portal_root)
                    cmd = it.get('cmd') or it.get('play_cmd') or it.get('command') or ''
                    url = client.link(cmd, 'series') or StalkerClient.clean_cmd(cmd)
                    if not url:
                        continue
                    out.append({'title': title, 'url': url, 'group': group, 'logo': logo, 'tvg-logo': logo, 'epg': '', 'is_vod': True, 'type': 'series'})
            cb(100, 'OK')
            return out

        raise Exception('Unsupported content type')
    except Exception as e:
        raise Exception(translate_error(e, host))


def parse_m3u_text(content):
    channels = []
    current = {}
    attr_re = re.compile(r'([\w-]+)="(.*?)"')
    for line in (content or '').splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('#EXTINF'):
            title = line.rsplit(',', 1)[1].strip() if ',' in line else 'No Name'
            attrs = {}
            try:
                attrs = {k.lower(): v for k, v in attr_re.findall(line.split(',', 1)[0])}
            except Exception:
                attrs = {}
            current = {
                'title': clean_name(attrs.get('tvg-name') or title),
                'group': clean_name(attrs.get('group-title') or attrs.get('group') or 'Main'),
                'logo': attrs.get('tvg-logo') or attrs.get('logo') or '',
                'epg_id': attrs.get('tvg-id') or attrs.get('epg-id') or attrs.get('id') or ''
            }
        elif (line.startswith('http') or '://' in line) and current:
            logo = current.get('logo') or ''
            epg_id = current.get('epg_id') or ''
            channels.append({
                'title': current.get('title') or 'No Name',
                'url': line,
                'group': current.get('group') or 'Main',
                'logo': logo,
                'tvg-logo': logo,
                'epg': '',
                'epg_id': epg_id,
                'tvg-id': epg_id,
                'is_adult': _is_adult_title_group(current.get('title'), current.get('group')),
            })
            current = {}
    return channels
