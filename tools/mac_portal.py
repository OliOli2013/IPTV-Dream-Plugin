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

def parse_mac_playlist(host, mac):
    """Parsuje playlistę z portalu MAC."""
    host = host.strip().rstrip('/')
    
    # 1. Próba Xtream (Szybka)
    host_xc = host[:-2] if host.endswith('/c') else host
    url_xc = f"{host_xc}/get.php?username={mac}&password={mac}&type=m3u_plus&output=ts"
    try:
        r = requests.get(url_xc, timeout=12, headers={'User-Agent': COMMON_UA}, verify=False)
        if r.status_code == 200 and "#EXTINF" in r.text:
            return parse_m3u_text(r.text)
    except:
        pass

    # 2. Próba Stalker
    host_stalker = f"{host}/c" if not host.endswith('/c') else host
    s = requests.Session()
    s.verify = False
    s.headers.update({
        'User-Agent': COMMON_UA,
        'Referer': f"{host_stalker}/",
        'Cookie': f'mac={mac}; stb_lang=en; timezone=Europe/London;'
    })

    try:
        sn = get_random_sn()
        token_url = f"{host_stalker}/server/load.php?type=stb&action=handshake&token=&mac={mac}&stb_type=MAG250&ver=ImageDescription: 0.2.18-r14-250; ImageDate: Fri Jan 15 15:20:44 EET 2016; PORTAL version: 5.1.0; API Version: JS API version: 328; STB API version: 134;&sn={sn}"
        
        r = s.get(token_url, timeout=REQ_TIMEOUT)
        r.raise_for_status()
        js = r.json()
        if not js or "js" not in js or "token" not in js["js"]:
            raise Exception("Auth Failed")
        token = js["js"]["token"]
        s.headers.update({'Authorization': f'Bearer {token}'})

        # Kategorie
        genres = {}
        try:
            r_g = s.get(f"{host_stalker}/server/load.php?type=itv&action=get_genres&token={token}", timeout=8)
            data_g = r_g.json()
            if "js" in data_g and isinstance(data_g["js"], list):
                for g in data_g["js"]:
                    genres[str(g.get("id"))] = clean_name(g.get("title", "Inne"))
        except: 
            pass

        # Kanały
        s.get(f"{host_stalker}/server/load.php?type=stb&action=get_profile&token={token}", timeout=5)
        r = s.get(f"{host_stalker}/server/load.php?type=itv&action=get_all_channels&token={token}", timeout=40)
        data = r.json()
        
        if "js" not in data or "data" not in data["js"]:
            raise Exception("Empty List")
            
        ch_list = data["js"]["data"]
        out = []
        for item in ch_list:
            name = clean_name(item.get("name", "No Name"))
            cmd = item.get("cmd", "")
            logo = item.get("logo", "")
            gid = str(item.get("tv_genre_id", ""))
            
            url_clean = cmd.replace("ffmpeg ", "").replace("auto ", "").replace("ch_id=", "")
            if "://" not in url_clean:
                url_clean = f"{host_stalker}/mpegts_to_ts/{url_clean}"
            if logo and not logo.startswith('http'):
                logo = f"{host_stalker}/{logo}"
                
            out.append({
                "title": name,
                "url": url_clean,
                "group": genres.get(gid, "Inne"),
                "logo": logo,
                "epg": ""
            })
        return out

    except Exception as e:
        friendly_msg = translate_error(e, host_stalker)
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