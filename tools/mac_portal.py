# -*- coding: utf-8 -*-
import json, os, requests, re, random, string, time
from .lang import _
from .logger import get_logger, mask_sensitive
from Components.Language import language

MAC_FILE = "/etc/enigma2/iptvdream_mac.json"
COMMON_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

# Timeout dla zapytań sieciowych (Bezpieczeństwo)
# Timeout dla zapytań sieciowych (wydłużony - duże portale potrafią odpowiadać wolniej)
REQ_TIMEOUT = 30

# Logger (writes to /tmp/iptvdream.log)
LOG_MAC = get_logger("IPTVDream.MAC", log_file="/tmp/iptvdream.log", debug=False)


def _mask_mac(mac):
    try:
        m = (mac or "").strip()
        m2 = m.replace(":", "").replace("-", "")
        if len(m2) >= 6:
            return "**:**:**:**:%s" % m2[-6:-4] + ":%s" % m2[-4:-2] + ":%s" % m2[-2:]
        if len(m2) >= 4:
            return "****" + m2[-4:]
    except Exception:
        pass
    return "****"


# Stalker/MAG często oczekuje parametru JsHttpRequest=1-xml (inaczej potrafi zwrócić HTML)
JS_HTTPREQUEST = '1-xml'


def _is_likely_json_bytes(b):
    try:
        if b is None:
            return False
        if isinstance(b, str):
            s = b.lstrip()
        else:
            s = b.decode('utf-8', 'ignore').lstrip()
        return s.startswith('{') or s.startswith('[')
    except Exception:
        return False


def _safe_json(resp):
    """Parse JSON defensively.

    Zamiast "Expecting value..." zwróć czytelniejszy błąd, jeśli serwer zwrócił HTML/pustą odpowiedź.
    """
    try:
        return resp.json()
    except Exception:
        try:
            raw = resp.content or b''
        except Exception:
            raw = b''
        if (not raw) or (not _is_likely_json_bytes(raw)):
            raise Exception('BAD_JSON_RESPONSE')
        raise

def load_mac_json():
    """Wczytuje listę portali. Obsługuje migrację ze starego formatu."""
    try:
        if not os.path.exists(MAC_FILE):
            return []
            
        # Odczyt głównego pliku; jeżeli jest uszkodzony (np. przerwany zapis),
        # spróbuj z kopii .bak.
        try:
            with open(MAC_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            bak = MAC_FILE + ".bak"
            if os.path.exists(bak):
                with open(bak, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                raise
            
        # Migracja: Jeśli stary format (słownik), zamień na listę
        if isinstance(data, dict) and "host" in data:
            new_data = [{"name": "Domyślny", "host": data["host"], "mac": data["mac"]}]
            save_mac_json(new_data)
            return new_data
            
        # Jeśli to już lista, zwróć ją
        if isinstance(data, list):
            return data
            
        return []
    except Exception:
        return []

def save_mac_json(data):
    """Zapisuje listę portali."""
    try:
        # Upewniamy się, że zapisujemy listę
        if not isinstance(data, list):
            data = [data] if data else []

        # Bezpieczny zapis atomowy: najpierw do pliku tymczasowego, potem rename.
        # Dodatkowo utrzymujemy kopię .bak, aby UI nie "gubił" portali po eksporcie/restarcie.
        base_dir = os.path.dirname(MAC_FILE)
        if base_dir and not os.path.exists(base_dir):
            try:
                os.makedirs(base_dir)
            except Exception:
                pass

        tmp_file = MAC_FILE + ".tmp"
        bak_file = MAC_FILE + ".bak"

        # Zapis do tmp
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            try:
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                pass

        # Kopia starego pliku (jeżeli istniał)
        if os.path.exists(MAC_FILE):
            try:
                import shutil
                shutil.copy2(MAC_FILE, bak_file)
            except Exception:
                pass

        # Atomowa podmiana
        try:
            os.replace(tmp_file, MAC_FILE)
        except Exception:
            # Python 2 fallback
            try:
                os.rename(tmp_file, MAC_FILE)
            except Exception:
                pass
    except Exception:
        pass

def add_mac_portal(host, mac):
    """Dodaje nowy portal do listy (WebIF/Ręcznie)."""
    portals = load_mac_json()
    
    # Sprawdź duplikaty
    for p in portals:
        if p.get("host") == host and p.get("mac") == mac:
            return # Już istnieje
            
    # Generuj nazwę
    name = f"Portal {len(portals) + 1}"
    try:
        domain = host.split("//")[-1].split("/")[0]
        name = domain
    except: 
        pass
    
    portals.append({"name": name, "host": host, "mac": mac})
    save_mac_json(portals)

def get_random_sn():
    """Generuje losowy numer seryjny."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=13))

def translate_error(e, url=""):
    """Tłumaczy błędy na przyjazne komunikaty."""
    lang = language.getLanguage()[:2] or "pl"
    err_str = str(e)
    if "404" in err_str: 
        return _("err_404", lang)
    if "401" in err_str or "403" in err_str: 
        return _("err_401", lang)
    if "auth failed" in err_str.lower():
        if lang == "pl":
            return "Błąd połączenia: Auth Failed.\nPortal nie zwrócił tokena (handshake).\nSprawdź MAC/URL i zobacz /tmp/iptvdream.log"
        return "Connection error: Auth Failed.\nPortal returned no token (handshake).\nCheck MAC/URL and see /tmp/iptvdream.log"
    if "500" in err_str or "502" in err_str: 
        return f"{_('err_server', lang)}.\n{_('try_later', lang)}"
    if "BAD_JSON_RESPONSE" in err_str or "Expecting value" in err_str:
        # Serwer zwrócił HTML/pustą odpowiedź (często redirect lub zły endpoint)
        if lang == 'pl':
            return "Portal zwrócił nieprawidłową odpowiedź (brak JSON).\nSprawdź URL (najlepiej końcówka /c/), port oraz czy portal nie przekierowuje na HTTPS."
        return "Portal returned invalid response (not JSON).\nCheck URL (prefer /c/), port and whether the portal redirects to HTTPS."
    if "timeout" in err_str.lower() or "connection" in err_str.lower(): 
        return _("err_timeout", lang)
    return f"{_('err_generic', lang)}:\n{err_str[:100]}..."

def clean_name(name):
    """Czyści nazwę kanału z nadmiarowych znaków."""
    if not name: 
        return "No Name"
    name = str(name).strip()
    name = re.sub(r'^\[.*?\]\s*', '', name)
    name = re.sub(r'^\(.*?\)\s*', '', name)
    return name.strip()

def _ensure_scheme(u):
    u = (u or '').strip()
    if not u:
        return u
    if not u.startswith('http://') and not u.startswith('https://'):
        u = 'http://' + u
    return u


def _split_portal_urls(host):
    """Returns (portal_ui, api_base).

    portal_ui is the UI path ending with '/c' (no trailing slash).
    api_base is the same without the trailing '/c'.
    """
    host = _ensure_scheme(host).strip().rstrip('/')
    # Strip common UI suffixes
    host = re.sub(r'/c/?$', '/c', host)
    if host.endswith('/c'):
        portal_ui = host
        api_base = host[:-2]
    else:
        portal_ui = host + '/c'
        api_base = host
    api_base = api_base.rstrip('/')
    portal_ui = portal_ui.rstrip('/')
    return portal_ui, api_base


def _candidate_loadphp(portal_ui, api_base):
    cands = [
        api_base + '/server/load.php',
        portal_ui + '/server/load.php',  # legacy/rare
        api_base + '/c/server/load.php', # legacy/rare
    ]
    out = []
    for u in cands:
        u = u.replace('//server/', '/server/')
        if u not in out:
            out.append(u)
    return out


def _js_data(js):
    if not js or 'js' not in js:
        return None
    v = js.get('js')
    if isinstance(v, dict) and 'data' in v:
        return v.get('data')
    return v


def _list_meta_from_response(js):
    """Extract (items, total_items, max_page_items) from Stalker 'get_ordered_list' JSON."""
    items = []
    total = None
    max_page = None
    try:
        j = js.get('js') if isinstance(js, dict) else None
        if isinstance(j, dict):
            items = j.get('data') if isinstance(j.get('data'), list) else []
            total = j.get('total_items') or j.get('total')
            max_page = j.get('max_page_items') or j.get('max_items') or j.get('page_items')
        elif isinstance(j, list):
            items = j
    except Exception:
        items = []
    try:
        total = int(total) if total is not None and str(total).isdigit() else None
    except Exception:
        total = None
    try:
        max_page = int(max_page) if max_page is not None and str(max_page).isdigit() else None
    except Exception:
        max_page = None
    if max_page is None:
        try:
            max_page = len(items) if items else 14
        except Exception:
            max_page = 14
    return items, total, max_page


def _iter_ordered_list(session, endpoint, token, kind, category_id, sortby='added'):
    """Iterate ordered_list pages robustly.

    Problem zgłaszany przez użytkowników: część portali zwraca tylko 14 pozycji (max_page_items=14),
    a kolejne strony są ignorowane, jeśli nie wykonano inicjalizacji profilu albo portal używa
    innych nazw parametrów paginacji.

    Ten iterator:
    - próbuje kilka wariantów paginacji (p 0-based, p 1-based, page, offset/limit, from/to),
    - zawsze wybiera najlepszą odpowiedź (nawet jeśli na danej stronie brak nowych wpisów),
    - kończy dopiero, gdy serwer przestanie zwracać dane lub wykryje pętlę.
    """
    seen = set()
    page = 0
    empty_streak = 0
    total_hint = None
    max_page = 14

    # normalize
    cat_val = str(category_id)

    while True:
        frm = page * max_page
        to = frm + max_page

        variants = [
            # standard stalker
            {'p': page},
            {'p': page + 1},
            # portals with different pagination keys
            {'page': page},
            {'page': page + 1},
            {'offset': frm, 'limit': max_page},
            {'offset': frm, 'count': max_page},
            {'start': frm, 'limit': max_page},
            # range style
            {'from': frm, 'to': to},
            {'p': page, 'from': frm, 'to': to},
            {'p': page + 1, 'from': frm, 'to': to},
        ]

        best_items = None
        best_new = -1  # allow selecting a response even if 0 new
        best_total = None
        best_max_page = None

        for v in variants:
            params = {
                'type': kind,
                'action': 'get_ordered_list',
                'category': cat_val,
                'sortby': sortby,
                'token': token,
                'JsHttpRequest': JS_HTTPREQUEST,
            }
            params.update(v)
            try:
                r = session.get(endpoint, params=params, timeout=REQ_TIMEOUT)
                r.raise_for_status()
                js = _safe_json(r)
            except Exception:
                continue

            items, total, mp = _list_meta_from_response(js)
            if total_hint is None and total is not None:
                total_hint = total
            if mp and mp > 0:
                best_max_page = mp

            if not isinstance(items, list):
                items = []

            # compute "new" count (heuristic)
            new_count = 0
            for it in items:
                iid = it.get('id') or it.get('movie_id') or it.get('vod_id') or it.get('series_id')
                # strengthen uniqueness if needed
                if iid is None:
                    # fallback signature: cmd+name
                    sig = (it.get('cmd') or it.get('name') or it.get('title') or '')[:128]
                    iid = "sig:" + sig
                if iid not in seen:
                    new_count += 1

            # select best response:
            # 1) prefer more new items
            # 2) if tie, prefer longer list
            if (new_count > best_new) or (new_count == best_new and best_items is not None and len(items) > len(best_items)) or (best_items is None and items):
                best_new = new_count
                best_items = items
                best_total = total
                if mp:
                    best_max_page = mp

        if best_max_page:
            max_page = int(best_max_page)

        if best_total is not None and total_hint is None:
            total_hint = best_total

        if not best_items:
            break

        new_any = False
        for it in best_items:
            iid = it.get('id') or it.get('movie_id') or it.get('vod_id') or it.get('series_id')
            if iid is None:
                sig = (it.get('cmd') or it.get('name') or it.get('title') or '')[:128]
                iid = "sig:" + sig
            if iid in seen:
                continue
            seen.add(iid)
            new_any = True
            yield it

        if not new_any:
            empty_streak += 1
        else:
            empty_streak = 0

        # safety: jeśli portal ignoruje paginację i zwraca w kółko tę samą stronę
        if empty_streak >= 3:
            break

        page += 1

        # jeśli znamy total_items i wiemy że już pobraliśmy >= total, zakończ
        if total_hint is not None:
            try:
                if len(seen) >= int(total_hint):
                    break
            except Exception:
                pass

def _extract_cmd_url(cmd, portal_root):
    if not cmd:
        return ''
    cmd = str(cmd)
    cmd = cmd.replace('ffmpeg ', '').replace('auto ', '').strip()
    # Some portals return cmd as 'ch_id=1234'
    cmd = cmd.replace('ch_id=', '')
    if '://' in cmd:
        return cmd
    # Live IPTV fallback
    return f"{portal_root}/mpegts_to_ts/{cmd}"


def _create_link(session, endpoint, token, kind, cmd):
    """Best-effort create_link for VOD/SERIES portals."""
    if not cmd:
        return ''
    cmd = str(cmd).replace('ffmpeg ', '').replace('auto ', '').strip()
    params = {
        'type': kind,
        'action': 'create_link',
        'cmd': cmd,
        'token': token,
    }
    # JsHttpRequest poprawia kompatybilność z częścią portali
    params['JsHttpRequest'] = JS_HTTPREQUEST
    r = session.get(endpoint, params=params, timeout=REQ_TIMEOUT)
    r.raise_for_status()
    js = _safe_json(r)
    j = js.get('js')
    # Typical shapes: {'js': {'cmd': 'ffmpeg http://...'}} or {'js': 'http://...'}
    if isinstance(j, dict):
        c = j.get('cmd') or j.get('url')
        if c:
            return str(c).replace('ffmpeg ', '').replace('auto ', '').strip()
    if isinstance(j, str):
        return j.replace('ffmpeg ', '').replace('auto ', '').strip()
    return ''



# --- v6.5: Robust Stalker/MAG portal discovery & handshake (based on patterns used in mature plugins) ---

MAG_UA = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 2 rev: 369 Safari/533.3"
MAG_XUA = "Model: MAG250; Link: WiFi"

try:
    # Python 2/3
    from urllib.parse import urlparse
except Exception:
    from urlparse import urlparse  # type: ignore


def _read_local_timezone():
    try:
        tz_path = "/etc/timezone"
        if os.path.exists(tz_path):
            with open(tz_path, "r") as f:
                tz = (f.read() or "").strip()
                if tz and "/" in tz and not tz.startswith("#"):
                    return tz
    except Exception:
        pass
    return "Europe/London"


def _domain_from_url(u):
    try:
        p = urlparse(_ensure_scheme(u))
        return p.netloc or (p.path.split("/")[0] if p.path else "")
    except Exception:
        return ""


def _base_url_from_host(host):
    """Return (base_url, host_path_hint).

    base_url: scheme://netloc (no trailing slash)
    host_path_hint: the path the user typed (may include /stalker_portal etc), normalized.
    """
    host = _ensure_scheme(host).strip()
    try:
        p = urlparse(host)
        base = "%s://%s" % (p.scheme or "http", p.netloc or "")
        path = (p.path or "").strip()
        if path and not path.startswith("/"):
            path = "/" + path
        return base.rstrip("/"), path.rstrip("/")
    except Exception:
        host = host.strip().rstrip("/")
        if "://" in host:
            base = host.split("://", 1)[0] + "://" + host.split("://", 1)[1].split("/", 1)[0]
        else:
            base = "http://" + host.split("/", 1)[0]
        path = ""
        return base.rstrip("/"), path.rstrip("/")


def _portal_prefix_from_url(u):
    """Infer portal_prefix ('/c', '/stalker_portal', '/portal', '/mag', '/something') from an UI URL."""
    try:
        p = urlparse(u)
        path = (p.path or "").lower()
        # common patterns
        for pref in ("/stalker_portal", "/portal", "/mag", "/stalker"):
            if pref + "/c/" in path or pref + "/c" in path:
                return pref
        if "/c/" in path or path.endswith("/c"):
            return "/c"
        # fallback: first segment
        seg = path.strip("/").split("/", 1)[0]
        return "/" + seg if seg else "/c"
    except Exception:
        return "/c"


def _mag_headers(host, mac, timezone=None):
    """Headers that mimic MAG STB (often required to avoid HTML / redirects)."""
    tz = timezone or _read_local_timezone()
    dom = _domain_from_url(host)
    hdr = {
        "Host": dom,
        "Accept": "*/*",
        "User-Agent": MAG_UA,
        "Accept-Encoding": "gzip, deflate",
        "X-User-Agent": MAG_XUA,
        "Connection": "close",
        "Pragma": "no-cache",
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Cookie": "mac=%s; stb_lang=en; timezone=%s;" % (mac, tz),
    }
    return hdr


def _safe_json_any(resp):
    """Like _safe_json but tolerates servers returning JSON as text."""
    try:
        return _safe_json(resp)
    except Exception:
        try:
            return json.loads(resp.text)
        except Exception:
            raise


def _extract_loader_path_from_stream(resp, ui_url):
    """Extract loader PHP path from portal UI (streaming). Returns path starting with '/' or None."""
    portal_prefix = _portal_prefix_from_url(ui_url)
    try:
        for line in resp.iter_lines():
            try:
                if isinstance(line, bytes):
                    line = line.decode("utf-8", "ignore")
            except Exception:
                continue
            line = (line or "").strip()
            if not line:
                continue
            # We stop early - the needed lines usually appear quickly
            if "this.ajax_loader" not in line and "ajax_loader" not in line:
                continue

            # Pattern 1: this.portal_protocol+'://'+this.portal_ip+'/'+this.portal_path+'/server/load.php'
            m = re.search(r'this\.portal_protocol\s*\+\s*[\'"]://[\'"]\s*\+\s*this\.portal_ip\s*\+\s*[\'"]/[\'"]\s*\+\s*this\.portal_path\s*\+\s*[\'"](/[^\'"]+)', line)
            if not m:
                # Pattern 2: this.portal_protocol+'://'+this.portal_ip+'/server/move.php'
                m = re.search(r'this\.portal_protocol\s*\+\s*[\'"]://[\'"]\s*\+\s*this\.portal_ip\s*\+\s*[\'"](/[^\'"]+)', line)
            if not m:
                # Pattern 3: this.portal_ip+'/portal.php'
                m = re.search(r'this\.portal_ip\s*\+\s*[\'"](/[^\'"]+)', line)
            if m:
                path = m.group(1)
                path = (portal_prefix + path).strip()
                path = re.sub(r"/+", "/", path)
                return path
    except Exception:
        pass
    return None


def _discover_stalker_endpoint(base_url, host_path_hint, headers):
    """Try to discover the correct load.php/portal.php endpoint by reading the UI page.

    Returns: (endpoint_url, portal_prefix, ui_url)
    """
    # If user already gave the endpoint explicitly, accept it.
    if host_path_hint and any(x in host_path_hint.lower() for x in ("/server/load.php", "portal.php", "load.php")):
        # normalize to absolute
        endpoint = base_url + host_path_hint
        endpoint = re.sub(r"/+", "/", endpoint.replace("://", "§§")).replace("§§", "://")
        portal_prefix = "/" + endpoint.split("://", 1)[1].split("/", 1)[1].split("/", 1)[0]
        if "/server/" in endpoint:
            # keep prefix like /stalker_portal or /c
            p = endpoint.split("://", 1)[1]
            path = "/" + p.split("/", 1)[1]
            portal_prefix = "/" + path.strip("/").split("/", 1)[0]
        ui_url = base_url + (portal_prefix + ("/c/" if portal_prefix != "/c" else "/")).replace("//", "/")
        ui_url = re.sub(r"/+", "/", ui_url.replace("://", "§§")).replace("§§", "://")
        return endpoint, portal_prefix, ui_url

    # Candidate UI URLs (ordered)
    ui_candidates = []
    # If user hinted a path (e.g. /stalker_portal), try it first.
    if host_path_hint:
        hint = host_path_hint.strip("/")
        if hint:
            if hint.endswith("c"):
                ui_candidates.append(base_url + "/" + hint + "/")
            else:
                ui_candidates.append(base_url + "/" + hint + "/c/")
            # also try /c/ directly under hinted path root
            if "/c" not in hint:
                ui_candidates.append(base_url + "/" + hint + "/c/")
    # Common defaults
    ui_candidates.extend([
        base_url + "/stalker_portal/c/",
        base_url + "/portal/c/",
        base_url + "/mag/c/",
        base_url + "/c/",
    ])
    # De-dup while preserving order
    seen = set()
    ui_candidates = [u for u in ui_candidates if not (u in seen or seen.add(u))]

    s = requests.Session()
    s.verify = False

    for ui in ui_candidates:
        try:
            r = s.get(ui, headers=headers, timeout=(6, 10), verify=False, allow_redirects=True, stream=True)
            r.raise_for_status()

            # quick heuristic: ensure it's really a portal UI
            try:
                # if redirected, update ui for prefix inference
                ui_final = r.url or ui
            except Exception:
                ui_final = ui

            path = _extract_loader_path_from_stream(r, ui_final)
            if path:
                endpoint = base_url + path
                endpoint = re.sub(r"/+", "/", endpoint.replace("://", "§§")).replace("§§", "://")
                portal_prefix = _portal_prefix_from_url(ui_final)
                return endpoint, portal_prefix, ui_final

            # fallback: some UIs embed 'server/load.php' plainly in HTML
            try:
                body = r.text or ""
                if "load.php" in body or "portal.php" in body:
                    # attempt simple locate
                    m = re.search(r'(/[^"\\\']*(?:server/)?load\.php)', body, re.IGNORECASE)
                    if not m:
                        m = re.search(r'(/[^"\\\']*portal\.php)', body, re.IGNORECASE)
                    if m:
                        path = m.group(1)
                        portal_prefix = _portal_prefix_from_url(ui_final)
                        # if path looks relative to portal_prefix, prefix it
                        if not path.startswith(portal_prefix):
                            path = portal_prefix + "/" + path.lstrip("/")
                        path = re.sub(r"/+", "/", path)
                        endpoint = base_url + path
                        endpoint = re.sub(r"/+", "/", endpoint.replace("://", "§§")).replace("§§", "://")
                        return endpoint, portal_prefix, ui_final
            except Exception:
                pass

        except Exception:
            continue

    # Ultimate fallbacks (most common)
    for path, pref in (
        ("/stalker_portal/server/load.php", "/stalker_portal"),
        ("/c/server/load.php", "/c"),
        ("/server/load.php", "/c"),
        ("/portal.php", "/c"),
    ):
        return base_url + path, pref, base_url + (pref + ("/c/" if pref != "/c" else "/")).replace("//", "/")

    # unreachable
    return base_url + "/server/load.php", "/c", base_url + "/c/"


def _perform_handshake(session, endpoint, headers, mac, referer=None):
    """Robust handshake (GET/POST + legacy params + 'missing' prehash).

    Fixes in v6.5:
    - try SIMPLE handshake first (like mature clients)
    - tolerate portals returning js as JSON-string
    - tolerate token at top-level
    """
    token = None
    token_random = ""

    # Headers (add referer if known)
    h = dict(headers or {})
    if referer and "Referer" not in h:
        h["Referer"] = referer
        try:
            # Origin helps some portals
            from urllib.parse import urlparse
            p = urlparse(referer)
            h["Origin"] = "%s://%s" % (p.scheme, p.netloc)
        except Exception:
            pass

    # Some portals reject unknown params in handshake – start minimal.
    variants = [
        # 1) simplest
        {"type": "stb", "action": "handshake", "JsHttpRequest": JS_HTTPREQUEST},
        # 2) with mac
        {"type": "stb", "action": "handshake", "JsHttpRequest": JS_HTTPREQUEST, "mac": mac},
    ]

    # Legacy MAG-ish (fallback)
    sn = get_random_sn()
    ver = 'ImageDescription: 0.2.18-r14-250; ImageDate: Fri Jan 15 15:20:44 EET 2016; PORTAL version: 5.1.0; API Version: JS API version: 328; STB API version: 134;'
    variants.append({
        "type": "stb",
        "action": "handshake",
        "token": "",
        "mac": mac,
        "stb_type": "MAG250",
        "ver": ver,
        "sn": sn,
        "JsHttpRequest": JS_HTTPREQUEST,
    })

    def _try(method, params, hdrs):
        try:
            if method == "get":
                r = session.get(endpoint, headers=hdrs, params=params, timeout=(6, 25), verify=False, allow_redirects=True)
            else:
                r = session.post(endpoint, headers=hdrs, params=params, data="", timeout=(6, 25), verify=False, allow_redirects=True)
            r.raise_for_status()
            return _safe_json_any(r)
        except Exception as e:
            try:
                LOG_MAC.info("handshake fail %s %s: %s", method.upper(), endpoint, mask_sensitive(e))
            except Exception:
                pass
            return None

    js = None
    for params in variants:
        # POST first – many portals expect this
        for method in ("post", "get"):
            js = _try(method, params, h)
            if js:
                break
        if js:
            break

    # Parse token
    if js and isinstance(js, dict):
        js_container = js.get("js")
        if isinstance(js_container, str):
            try:
                js_container = json.loads(js_container)
            except Exception:
                js_container = None
        j = js_container if isinstance(js_container, dict) else {}

        # Some portals keep token on top-level
        token = (j.get("token") if isinstance(j, dict) else None) or js.get("token")
        token_random = (j.get("random") if isinstance(j, dict) else "") or js.get("random", "") or ""

        # Some portals require prehash (msg: missing)
        try:
            msg = (j.get("msg") or "").lower()
        except Exception:
            msg = ""

        if (not token) and ("missing" in msg):
            try:
                import hashlib
                fake = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))
                prehash = hashlib.sha1(fake.encode("utf-8")).hexdigest()
                headers2 = dict(h)
                headers2["Authorization"] = "Bearer " + fake
                params3 = {"type": "stb", "action": "handshake", "JsHttpRequest": JS_HTTPREQUEST, "mac": mac, "prehash": prehash}
                js2 = _try("post", params3, headers2) or _try("get", params3, headers2)
                if js2 and isinstance(js2, dict):
                    js_container2 = js2.get("js")
                    if isinstance(js_container2, str):
                        try:
                            js_container2 = json.loads(js_container2)
                        except Exception:
                            js_container2 = None
                    j2 = js_container2 if isinstance(js_container2, dict) else {}
                    token = j2.get("token") or js2.get("token")
                    token_random = j2.get("random", "") or js2.get("random", "") or token_random
            except Exception as e:
                try:
                    LOG_MAC.info("handshake missing/prehash error: %s", mask_sensitive(e))
                except Exception:
                    pass

    return token, token_random


def _make_profile_params(endpoint, mac, token_random=""):
    """Generate get_profile params similar to what mature clients send (kept minimal)."""
    try:
        import hashlib
        sn = hashlib.md5(mac.encode("utf-8")).hexdigest().upper()[:13]
        device_id = hashlib.sha256(mac.encode("utf-8")).hexdigest().upper()
        device_id2 = device_id
        hw_version_2 = hashlib.sha1(mac.encode("utf-8")).hexdigest()
        prehash = hashlib.sha1((sn + mac).encode("utf-8")).hexdigest()
    except Exception:
        sn = get_random_sn()
        device_id = sn
        device_id2 = sn
        hw_version_2 = sn
        prehash = ""

    ts = int(time.time())
    # Metrics payload (encoded once)
    metrics = {"mac": mac, "sn": sn, "type": "STB", "model": "MAG250", "uid": "", "random": token_random or ""}
    try:
        from urllib.parse import quote
    except Exception:
        from urllib import quote  # type: ignore
    metrics_enc = quote(json.dumps(metrics))

    params = {
        "type": "stb",
        "action": "get_profile",
        "JsHttpRequest": JS_HTTPREQUEST,
        "mac": mac,
        "hd": "1",
        "ver": "ImageDescription: 0.2.18-r14-pub-250; ImageDate: Fri Jan 15 15:20:44 EET 2016; PORTAL version: 5.3.0; API Version: JS API version: 328; STB API version: 134; Player Engine version: 0x566",
        "num_banks": "2",
        "sn": sn,
        "stb_type": "MAG250",
        "client_type": "STB",
        "image_version": "218",
        "video_out": "hdmi",
        "device_id": device_id,
        "device_id2": device_id2,
        "signature": "",
        "auth_second_step": "1",
        "hw_version": "1.7-BD-00",
        "hw_version_2": hw_version_2,
        "not_valid_token": "0",
        "metrics": metrics_enc,
        "timestamp": str(ts),
        "api_signature": "261",
    }
    if prehash:
        params["prehash"] = prehash
    return params


def _handshake(host, mac):
    """Returns (session, endpoint, token, headers_auth, portal_root, portal_ui)."""
    base_url, hint_path = _base_url_from_host(host)

    # Normalize MAC (keep colons if present)
    mac = (mac or '').strip().upper()

    headers = _mag_headers(base_url, mac, timezone=_read_local_timezone())

    endpoint0, portal_prefix0, ui_url0 = _discover_stalker_endpoint(base_url, hint_path, headers)

    s = requests.Session()
    s.verify = False
    try:
        s.headers.update(headers)
    except Exception:
        pass

    # Warm-up UI to pick up cookies (some portals require session cookie before handshake)
    ui_final = ui_url0
    try:
        r0 = s.get(ui_url0, headers=headers, timeout=(6, 12), verify=False, allow_redirects=True)
        if getattr(r0, 'url', None):
            ui_final = r0.url
    except Exception as e:
        try:
            LOG_MAC.info('UI warmup fail %s: %s', ui_url0, mask_sensitive(e))
        except Exception:
            pass

    def _infer_prefix_from_endpoint(ep):
        try:
            from urllib.parse import urlparse
        except Exception:
            from urlparse import urlparse  # type: ignore
        try:
            p = urlparse(ep)
            path = (p.path or '')
        except Exception:
            path = ''
        path = path.split('?', 1)[0]
        # remove known suffixes
        for suf in ('/server/load.php', '/portal.php', '/server/load.php/', '/portal.php/'):
            if path.endswith(suf):
                pref = path[:-len(suf)]
                pref = pref.rstrip('/')
                return pref
        # fallback: first segment
        seg = path.strip('/').split('/', 1)[0]
        return '/' + seg if seg else ''

    # Candidate endpoints
    cands = []
    def _add(u):
        if not u:
            return
        u = u.strip()
        if u and u not in cands:
            cands.append(u)

    _add(endpoint0)

    # Generate alternatives based on common layouts
    for pref in [portal_prefix0, '/stalker_portal', '/portal', '/mag', '/c', '']:
        if pref == '/c':
            _add(base_url + '/c/server/load.php')
            _add(base_url + '/c/portal.php')
        elif pref:
            _add(base_url + pref + '/server/load.php')
            _add(base_url + pref + '/portal.php')
        else:
            _add(base_url + '/server/load.php')
            _add(base_url + '/portal.php')

    token = None
    token_random = ''
    endpoint = endpoint0
    portal_prefix = portal_prefix0

    for ep in cands:
        pref = _infer_prefix_from_endpoint(ep)
        # build referer UI
        if pref:
            ui_try = (base_url + pref + '/c/').replace('//c/', '/c/')
        else:
            ui_try = base_url + '/c/'
        referer = ui_final or ui_try
        try:
            LOG_MAC.info('Handshake try endpoint=%s mac=%s', ep, _mask_mac(mac))
        except Exception:
            pass
        t, tr = _perform_handshake(s, ep, headers, mac, referer=referer)
        if t:
            token = t
            token_random = tr or ''
            endpoint = ep
            portal_prefix = pref
            break

    if not token:
        try:
            LOG_MAC.error('Auth Failed for host=%s mac=%s (no token)', host, _mask_mac(mac))
        except Exception:
            pass
        raise Exception('Auth Failed')

    # Set auth
    headers_auth = dict(headers)
    headers_auth['Authorization'] = 'Bearer ' + token
    try:
        s.headers.update(headers_auth)
    except Exception:
        pass

    # get_profile (best-effort)
    try:
        prof_params = _make_profile_params(endpoint, mac, token_random=token_random)
        s.get(endpoint, headers=headers_auth, params=prof_params, timeout=REQ_TIMEOUT, verify=False, allow_redirects=True)
    except Exception as e:
        try:
            LOG_MAC.info('get_profile fail: %s', mask_sensitive(e))
        except Exception:
            pass

    portal_root = (base_url + (portal_prefix or '')).rstrip('/')
    if portal_prefix == '/c':
        portal_ui = portal_root
    elif portal_prefix:
        portal_ui = portal_root + '/c'
    else:
        portal_ui = base_url.rstrip('/') + '/c'

    return s, endpoint, token, headers_auth, portal_root, portal_ui



def parse_mac_playlist(host, mac, content_type='live', progress_callback=None):
    """Parsuje playlistę z portalu MAC/Stalker.

    content_type: 'live' | 'vod' | 'series'

    progress_callback: optional callable(pct:int, msg:str)
    """
    host = (host or '').strip()
    mac = (mac or '').strip()
    if not host or not mac:
        raise Exception('Missing host/mac')

    try:
        LOG_MAC.info('MAC start type=%s host=%s mac=%s', content_type, host, _mask_mac(mac))
    except Exception:
        pass

    def _cb(pct, msg=""):
        try:
            if not progress_callback:
                return
            try:
                from twisted.internet import reactor
                reactor.callFromThread(progress_callback, int(pct), msg or "")
            except Exception:
                progress_callback(int(pct), msg or "")
        except Exception:
            pass

    base_url, _hint_path = _base_url_from_host(host)

    # (opcjonalnie) szybka próba m3u dla LIVE - nie wszystkie portale to wspierają
    if content_type == 'live':
        url_xc = "%s/get.php?username=%s&password=%s&type=m3u_plus&output=ts" % (base_url, mac, mac)
        try:
            r = requests.get(url_xc, timeout=10, headers={'User-Agent': COMMON_UA}, verify=False, allow_redirects=True)
            if r.status_code == 200 and '#EXTINF' in (r.text or ''):
                _cb(100, "OK")
                return parse_m3u_text(r.text)
        except Exception:
            pass

    try:
        _cb(2, "Handshake")
        s, endpoint, token, _hdr, portal_root, portal_ui = _handshake(host, mac)

        # --- LIVE ---
        if content_type == 'live':
            genres = {}
            _cb(5, "Genres")
            try:
                r_g = s.get(endpoint, params={'type': 'itv', 'action': 'get_genres', 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
                data_g = _safe_json_any(r_g)
                lst = _js_data(data_g)
                if isinstance(lst, list):
                    for g in lst:
                        genres[str(g.get('id'))] = clean_name(g.get('title', 'Inne'))
            except Exception:
                pass

            _cb(15, "Channels")
            r = s.get(endpoint, params={'type': 'itv', 'action': 'get_all_channels', 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
            r.raise_for_status()
            data = _safe_json_any(r)
            ch_list = None
            jsd = data.get('js') if isinstance(data, dict) else None
            if isinstance(jsd, dict):
                ch_list = jsd.get('data')
            if not isinstance(ch_list, list):
                raise Exception('Empty List')

            out = []
            total = len(ch_list) or 1
            for i, item in enumerate(ch_list):
                if i % 50 == 0:
                    _cb(15 + int((i / float(total)) * 80.0), "LIVE %d/%d" % (i, total))
                name = clean_name(item.get('name', 'No Name'))
                cmd = item.get('cmd', '')
                logo = item.get('logo', '')
                gid = str(item.get('tv_genre_id', ''))
                url_clean = _extract_cmd_url(cmd, portal_root)
                if logo and not str(logo).startswith('http'):
                    logo = "%s/%s" % (portal_root, str(logo).lstrip('/'))
                out.append({'title': name, 'url': url_clean, 'group': genres.get(gid, 'Inne'), 'logo': logo, 'epg': ''})

            _cb(100, "OK")
            return out

        # --- VOD ---
        if content_type == 'vod':
            _cb(5, "VOD categories")
            r_c = s.get(endpoint, params={'type': 'vod', 'action': 'get_categories', 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
            r_c.raise_for_status()
            cats = _js_data(_safe_json_any(r_c))
            if not isinstance(cats, list):
                cats = []

            out = []
            total_cats = len(cats) or 1
            processed = 0
            for cidx, cat in enumerate(cats):
                cat_id = cat.get('id')
                cat_title = clean_name(cat.get('title') or cat.get('name') or 'VOD')
                if cat_id is None:
                    continue

                _cb(5 + int((cidx / float(total_cats)) * 20.0), "VOD: %s" % cat_title)

                for it in _iter_ordered_list(s, endpoint, token, 'vod', cat_id, sortby='added'):
                    processed += 1
                    if processed % 100 == 0:
                        _cb(30 + min(69, int((cidx / float(total_cats)) * 60.0)), "VOD items: %d" % processed)
                    title = clean_name(it.get('name') or it.get('title') or 'VOD')
                    cmd = it.get('cmd') or it.get('cmds') or ''
                    logo = it.get('screenshot_uri') or it.get('poster') or it.get('cover') or ''
                    url = ''
                    try:
                        if cmd:
                            url = _create_link(s, endpoint, token, 'vod', cmd)
                    except Exception:
                        url = ''
                    if not url and cmd:
                        url = cmd.replace('ffmpeg ', '').replace('auto ', '').strip()
                    if logo and not str(logo).startswith('http'):
                        logo = "%s/%s" % (portal_root, str(logo).lstrip('/'))
                    if url:
                        out.append({'title': title, 'url': url, 'group': cat_title, 'logo': logo, 'epg': ''})

            _cb(100, "OK")
            return out

        # --- SERIES ---
        if content_type == 'series':
            _cb(5, "Series categories")
            r_c = s.get(endpoint, params={'type': 'series', 'action': 'get_categories', 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
            r_c.raise_for_status()
            cats = _js_data(_safe_json_any(r_c))
            if not isinstance(cats, list):
                cats = []

            out = []
            total_cats = len(cats) or 1
            processed = 0

            for cidx, cat in enumerate(cats):
                cat_id = cat.get('id')
                cat_title = clean_name(cat.get('title') or cat.get('name') or 'Series')
                if cat_id is None:
                    continue

                _cb(5 + int((cidx / float(total_cats)) * 20.0), "Series: %s" % cat_title)

                for ser in _iter_ordered_list(s, endpoint, token, 'series', cat_id, sortby='added'):
                    processed += 1
                    if processed % 50 == 0:
                        _cb(30 + min(69, int((cidx / float(total_cats)) * 60.0)), "Series items: %d" % processed)

                    sid = ser.get('id') or ser.get('movie_id') or ser.get('series_id')
                    series_title = clean_name(ser.get('name') or ser.get('title') or 'Series')
                    logo = ser.get('screenshot_uri') or ser.get('poster') or ser.get('cover') or ''
                    if logo and not str(logo).startswith('http'):
                        logo = "%s/%s" % (portal_root, str(logo).lstrip('/'))

                    # Expand to seasons/episodes (best-effort)
                    seasons = []
                    if sid is not None:
                        for key in ('movie_id', 'series_id', 'id'):
                            try:
                                r_s = s.get(endpoint, params={'type': 'series', 'action': 'get_seasons', key: sid, 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
                                r_s.raise_for_status()
                                seasons = _js_data(_safe_json_any(r_s))
                                if isinstance(seasons, list):
                                    break
                            except Exception:
                                seasons = []

                    if isinstance(seasons, list) and seasons:
                        for season in seasons:
                            season_id = season.get('id') or season.get('season_id')
                            snum = season.get('number') or season.get('season_number')
                            try:
                                snum_i = int(snum) if snum is not None else None
                            except Exception:
                                snum_i = None

                            episodes = []
                            if season_id is not None and sid is not None:
                                for movie_key in ('movie_id', 'series_id', 'id'):
                                    try:
                                        r_e = s.get(endpoint, params={'type': 'series', 'action': 'get_episodes', movie_key: sid, 'season_id': season_id, 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
                                        r_e.raise_for_status()
                                        episodes = _js_data(_safe_json_any(r_e))
                                        if isinstance(episodes, list):
                                            break
                                    except Exception:
                                        episodes = []

                            if not isinstance(episodes, list) or not episodes:
                                continue

                            for ep in episodes:
                                ep_title = clean_name(ep.get('name') or ep.get('title') or 'Episode')
                                enum = ep.get('number') or ep.get('episode_number') or ep.get('episode')
                                try:
                                    enum_i = int(enum) if enum is not None else None
                                except Exception:
                                    enum_i = None

                                cmd = ep.get('cmd') or ep.get('cmds') or ''
                                url = ''
                                try:
                                    if cmd:
                                        url = _create_link(s, endpoint, token, 'series', cmd)
                                except Exception:
                                    url = ''
                                if not url and cmd:
                                    url = cmd.replace('ffmpeg ', '').replace('auto ', '').strip()
                                if not url:
                                    continue

                                parts = [series_title]
                                if snum_i is not None or enum_i is not None:
                                    s_part = ("S%02d" % (snum_i or 0)) if snum_i is not None else "S??"
                                    e_part = ("E%02d" % (enum_i or 0)) if enum_i is not None else "E??"
                                    parts.append("%s%s" % (s_part, e_part))
                                if ep_title and ep_title.lower() not in (series_title.lower(), 'episode'):
                                    parts.append(ep_title)
                                title = ' - '.join(parts)

                                out.append({'title': title, 'url': url, 'group': cat_title, 'logo': logo, 'epg': ''})
                    else:
                        # Fallback: series without seasons/episodes
                        cmd = ser.get('cmd') or ser.get('cmds') or ''
                        url = ''
                        try:
                            if cmd:
                                url = _create_link(s, endpoint, token, 'series', cmd)
                        except Exception:
                            url = ''
                        if not url and cmd:
                            url = cmd.replace('ffmpeg ', '').replace('auto ', '').strip()
                        if url:
                            out.append({'title': series_title, 'url': url, 'group': cat_title, 'logo': logo, 'epg': ''})

            _cb(100, "OK")
            return out

        raise Exception('Unsupported content type')

    except Exception as e:
        # translate_error already produces user-friendly message (PL/EN)
        friendly_msg = translate_error(e, host)
        raise Exception(friendly_msg)


def parse_m3u_text(content):
    """Parsuje tekst M3U do listy kanałów."""
    channels = []
    current_info = {}
    for line in content.splitlines():
        line = line.strip()
        if not line: 
            continue
        if line.startswith('#EXTINF'):
            title = line.rsplit(',', 1)[1].strip() if ',' in line else "No Name"
            current_info = {"title": clean_name(title), "group": "Main"}
        elif line.startswith('http') and current_info:
            channels.append({
                "title": current_info["title"],
                "url": line.strip(),
                "group": current_info["group"],
                "logo": "",
                "epg": ""
            })
            current_info = {}
    return channels