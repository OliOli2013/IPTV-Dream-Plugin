# -*- coding: utf-8 -*-
import json, os, requests, re, random, string
from .lang import _
from Components.Language import language

MAC_FILE = "/etc/enigma2/iptvdream_mac.json"
COMMON_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

# Timeout dla zapytań sieciowych (Bezpieczeństwo)
# Timeout dla zapytań sieciowych (wydłużony - duże portale potrafią odpowiadać wolniej)
REQ_TIMEOUT = 30

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
    r = session.get(endpoint, params=params, timeout=REQ_TIMEOUT)
    r.raise_for_status()
    js = r.json()
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
            r = s.get(ep, params=params, timeout=REQ_TIMEOUT)
            r.raise_for_status()
            js = r.json()
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

        # Genres for LIVE
        genres = {}
        if content_type == 'live':
            try:
                r_g = s.get(endpoint, params={'type': 'itv', 'action': 'get_genres', 'token': token}, timeout=REQ_TIMEOUT)
                data_g = r_g.json()
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
                s.get(endpoint, params={'type': 'stb', 'action': 'get_profile', 'token': token}, timeout=REQ_TIMEOUT)
            except Exception:
                pass

            r = s.get(endpoint, params={'type': 'itv', 'action': 'get_all_channels', 'token': token}, timeout=REQ_TIMEOUT)
            r.raise_for_status()
            data = r.json()
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
            r_c = s.get(endpoint, params={'type': 'vod', 'action': 'get_categories', 'token': token}, timeout=REQ_TIMEOUT)
            r_c.raise_for_status()
            cats = _js_data(r_c.json())
            if not isinstance(cats, list):
                cats = []

            for cat in cats:
                cat_id = cat.get('id')
                cat_title = clean_name(cat.get('title') or cat.get('name') or 'VOD')
                if cat_id is None:
                    continue

                seen_ids = set()
                p = 0
                while True:
                    r_l = s.get(endpoint, params={
                        'type': 'vod',
                        'action': 'get_ordered_list',
                        'category': cat_id,
                        'p': p,
                        'sortby': 'added',
                        'token': token,
                    }, timeout=REQ_TIMEOUT)
                    r_l.raise_for_status()
                    js = r_l.json()
                    lst = _js_data(js)
                    if isinstance(lst, dict) and 'data' in lst:
                        lst = lst.get('data')
                    if not (isinstance(lst, list) and lst):
                        break

                    new_on_page = 0
                    for it in lst:
                        item_id = it.get('id') or it.get('movie_id') or it.get('vod_id')
                        if item_id is not None:
                            if item_id in seen_ids:
                                continue
                            seen_ids.add(item_id)
                        new_on_page += 1

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

                    if new_on_page == 0:
                        break
                    p += 1

            return out

        # --- SERIES ---
        if content_type == 'series':
            r_c = s.get(endpoint, params={'type': 'series', 'action': 'get_categories', 'token': token}, timeout=REQ_TIMEOUT)
            r_c.raise_for_status()
            cats = _js_data(r_c.json())
            if not isinstance(cats, list):
                cats = []

            for cat in cats:
                cat_id = cat.get('id')
                cat_title = clean_name(cat.get('title') or cat.get('name') or 'Series')
                if cat_id is None:
                    continue

                seen_series = set()
                p = 0
                while True:
                    r_l = s.get(endpoint, params={
                        'type': 'series',
                        'action': 'get_ordered_list',
                        'category': cat_id,
                        'p': p,
                        'sortby': 'added',
                        'token': token,
                    }, timeout=REQ_TIMEOUT)
                    r_l.raise_for_status()
                    js = r_l.json()
                    lst = _js_data(js)
                    if isinstance(lst, dict) and 'data' in lst:
                        lst = lst.get('data')
                    if not (isinstance(lst, list) and lst):
                        break

                    new_on_page = 0
                    for ser in lst:
                        sid = ser.get('id') or ser.get('movie_id') or ser.get('series_id')
                        if sid is not None:
                            if sid in seen_series:
                                continue
                            seen_series.add(sid)
                        new_on_page += 1

                        series_title = clean_name(ser.get('name') or ser.get('title') or 'Series')
                        logo = ser.get('screenshot_uri') or ser.get('poster') or ser.get('cover') or ''
                        if logo and not str(logo).startswith('http'):
                            logo = f"{portal_ui}/{str(logo).lstrip('/')}"

                        # Try to expand to seasons/episodes
                        seasons = []
                        if sid is not None:
                            for key in ('movie_id', 'series_id', 'id'):
                                try:
                                    r_s = s.get(endpoint, params={'type': 'series', 'action': 'get_seasons', key: sid, 'token': token}, timeout=REQ_TIMEOUT)
                                    r_s.raise_for_status()
                                    seasons = _js_data(r_s.json())
                                    if isinstance(seasons, list):
                                        break
                                except Exception:
                                    seasons = []

                        if isinstance(seasons, list) and seasons:
                            for season in seasons:
                                season_id = season.get('id') or season.get('season_id')
                                # season number best-effort
                                snum = season.get('number') or season.get('season_number')
                                try:
                                    snum_i = int(snum)
                                except Exception:
                                    snum_i = None

                                episodes = []
                                if season_id is not None and sid is not None:
                                    for movie_key in ('movie_id', 'series_id', 'id'):
                                        try:
                                            r_e = s.get(endpoint, params={'type': 'series', 'action': 'get_episodes', movie_key: sid, 'season_id': season_id, 'token': token}, timeout=REQ_TIMEOUT)
                                            r_e.raise_for_status()
                                            episodes = _js_data(r_e.json())
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
                                        enum_i = int(enum)
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

                                    # Build readable title
                                    parts = [series_title]
                                    if snum_i is not None or enum_i is not None:
                                        s_part = f"S{(snum_i or 0):02d}" if snum_i is not None else "S??"
                                        e_part = f"E{(enum_i or 0):02d}" if enum_i is not None else "E??"
                                        parts.append(f"{s_part}{e_part}")
                                    if ep_title and ep_title.lower() not in (series_title.lower(), 'episode'):
                                        parts.append(ep_title)
                                    title = ' - '.join(parts)

                                    out.append({'title': title, 'url': url, 'group': cat_title, 'logo': logo, 'epg': ''})

                        else:
                            # Fallback: export series items as single entries if portal returns cmd
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

                    if new_on_page == 0:
                        break
                    p += 1

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