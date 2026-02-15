# -*- coding: utf-8 -*-
import json, os, requests, re, random, string
from .lang import _
from Components.Language import language

MAC_FILE = "/etc/enigma2/iptvdream_mac.json"
COMMON_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

# Timeout dla zapytań sieciowych (Bezpieczeństwo)
# Timeout dla zapytań sieciowych (wydłużony - duże portale potrafią odpowiadać wolniej)
REQ_TIMEOUT = 30

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

def _extract_cmd_url(cmd, portal_ui):
    if not cmd:
        return ''
    cmd = str(cmd)
    cmd = cmd.replace('ffmpeg ', '').replace('auto ', '').strip()
    # Some portals return cmd as 'ch_id=1234'
    cmd = cmd.replace('ch_id=', '')
    if '://' in cmd:
        return cmd
    # Live IPTV fallback
    return f"{portal_ui}/mpegts_to_ts/{cmd}"


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


def _handshake(portal_ui, endpoints, mac):
    s = requests.Session()
    s.verify = False
    s.headers.update({
        'User-Agent': COMMON_UA,
        'Referer': f"{portal_ui}/",
        'Cookie': f'mac={mac}; stb_lang=en; timezone=Europe/London;'
    })

    sn = get_random_sn()
    ver = 'ImageDescription: 0.2.18-r14-250; ImageDate: Fri Jan 15 15:20:44 EET 2016; PORTAL version: 5.1.0; API Version: JS API version: 328; STB API version: 134;'

    last_err = None
    for ep in endpoints:
        try:
            params = {
                'type': 'stb',
                'action': 'handshake',
                'token': '',
                'mac': mac,
                'stb_type': 'MAG250',
                'ver': ver,
                'sn': sn,
            }
            params['JsHttpRequest'] = JS_HTTPREQUEST
            r = s.get(ep, params=params, timeout=REQ_TIMEOUT)
            r.raise_for_status()
            js = _safe_json(r)
            token = None
            if isinstance(js, dict):
                j = js.get('js')
                if isinstance(j, dict):
                    token = j.get('token')
            if token:
                s.headers.update({'Authorization': f'Bearer {token}'})
                return s, ep, token
        except Exception as e:
            last_err = e
            continue

    raise last_err or Exception('Auth Failed')


def parse_mac_playlist(host, mac, content_type='live'):
    """Parsuje playlistę z portalu MAC/Stalker.

    content_type: 'live' | 'vod' | 'series'
    """
    host = (host or '').strip()
    mac = (mac or '').strip()
    if not host or not mac:
        raise Exception('Missing host/mac')

    portal_ui, api_base = _split_portal_urls(host)

    # 1) Próba Xtream (szybka) — tylko LIVE
    if content_type == 'live':
        host_xc = api_base
        url_xc = f"{host_xc}/get.php?username={mac}&password={mac}&type=m3u_plus&output=ts"
        try:
            r = requests.get(url_xc, timeout=12, headers={'User-Agent': COMMON_UA}, verify=False)
            if r.status_code == 200 and '#EXTINF' in r.text:
                return parse_m3u_text(r.text)
        except Exception:
            pass

    # 2) Stalker/MAG API
    endpoints = _candidate_loadphp(portal_ui, api_base)

    try:
        s, endpoint, token = _handshake(portal_ui, endpoints, mac)

        # Inicjalizacja profilu STB - część portali bez tego nie paginuje poprawnie (max 14).
        try:
            s.get(endpoint, params={'type': 'stb', 'action': 'get_profile', 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
        except Exception:
            pass

        # Genres for LIVE
        genres = {}
        if content_type == 'live':
            try:
                r_g = s.get(endpoint, params={'type': 'itv', 'action': 'get_genres', 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
                data_g = _safe_json(r_g)
                lst = _js_data(data_g)
                if isinstance(lst, list):
                    for g in lst:
                        genres[str(g.get('id'))] = clean_name(g.get('title', 'Inne'))
            except Exception:
                pass

        out = []

        if content_type == 'live':
            # Profile + channels
            try:
                s.get(endpoint, params={'type': 'stb', 'action': 'get_profile', 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
            except Exception:
                pass

            r = s.get(endpoint, params={'type': 'itv', 'action': 'get_all_channels', 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
            r.raise_for_status()
            data = _safe_json(r)
            ch_list = None
            jsd = data.get('js')
            if isinstance(jsd, dict):
                ch_list = jsd.get('data')
            if not isinstance(ch_list, list):
                raise Exception('Empty List')

            for item in ch_list:
                name = clean_name(item.get('name', 'No Name'))
                cmd = item.get('cmd', '')
                logo = item.get('logo', '')
                gid = str(item.get('tv_genre_id', ''))

                url_clean = _extract_cmd_url(cmd, portal_ui)
                if logo and not str(logo).startswith('http'):
                    logo = f"{portal_ui}/{str(logo).lstrip('/')}"

                out.append({
                    'title': name,
                    'url': url_clean,
                    'group': genres.get(gid, 'Inne'),
                    'logo': logo,
                    'epg': ''
                })

            return out

        # --- VOD ---
        if content_type == 'vod':
            # categories
            r_c = s.get(endpoint, params={'type': 'vod', 'action': 'get_categories', 'token': token, 'JsHttpRequest': JS_HTTPREQUEST}, timeout=REQ_TIMEOUT)
            r_c.raise_for_status()
            cats = _js_data(_safe_json(r_c))
            if not isinstance(cats, list):
                cats = []

            for cat in cats:
                cat_id = cat.get('id')
                cat_title = clean_name(cat.get('title') or cat.get('name') or 'VOD')
                if cat_id is None:
                    continue

                for it in _iter_ordered_list(s, endpoint, token, 'vod', cat_id, sortby='added'):
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
                        logo = f"{portal_ui}/{str(logo).lstrip('/')}"

                    if url:
                        out.append({'title': title, 'url': url, 'group': cat_title, 'logo': logo, 'epg': ''})

            return out        # --- SERIES ---
        if content_type == 'series':
            r_c = s.get(
                endpoint,
                params={'type': 'series', 'action': 'get_categories', 'token': token, 'JsHttpRequest': JS_HTTPREQUEST},
                timeout=REQ_TIMEOUT,
            )
            r_c.raise_for_status()
            cats = _js_data(_safe_json(r_c))
            if not isinstance(cats, list):
                cats = []

            for cat in cats:
                cat_id = cat.get('id')
                cat_title = clean_name(cat.get('title') or cat.get('name') or 'Series')
                if cat_id is None:
                    continue

                for ser in _iter_ordered_list(s, endpoint, token, 'series', cat_id, sortby='added'):
                    sid = ser.get('id') or ser.get('movie_id') or ser.get('series_id')
                    series_title = clean_name(ser.get('name') or ser.get('title') or 'Series')
                    logo = ser.get('screenshot_uri') or ser.get('poster') or ser.get('cover') or ''
                    if logo and not str(logo).startswith('http'):
                        logo = f"{portal_ui}/{str(logo).lstrip('/')}"

                    # Expand to seasons/episodes (best-effort; zależne od portalu)
                    seasons = []
                    if sid is not None:
                        for key in ('movie_id', 'series_id', 'id'):
                            try:
                                r_s = s.get(
                                    endpoint,
                                    params={'type': 'series', 'action': 'get_seasons', key: sid, 'token': token, 'JsHttpRequest': JS_HTTPREQUEST},
                                    timeout=REQ_TIMEOUT,
                                )
                                r_s.raise_for_status()
                                seasons = _js_data(_safe_json(r_s))
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
                                        r_e = s.get(
                                            endpoint,
                                            params={'type': 'series', 'action': 'get_episodes', movie_key: sid, 'season_id': season_id, 'token': token, 'JsHttpRequest': JS_HTTPREQUEST},
                                            timeout=REQ_TIMEOUT,
                                        )
                                        r_e.raise_for_status()
                                        episodes = _js_data(_safe_json(r_e))
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
                        # Fallback: jeśli portal zwraca cmd bez odcinków
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

            return out

        raise Exception('Unsupported content type')

    except Exception as e:
        friendly_msg = translate_error(e, portal_ui)
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