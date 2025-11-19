# -*- coding: utf-8 -*-
import json, os, requests, re, random, string

MAC_FILE = "/etc/enigma2/iptvdream_mac.json"
COMMON_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

def load_mac_json():
    try:
        with open(MAC_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_mac_json(data):
    try:
        with open(MAC_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def get_random_sn():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=13))

def translate_error(e, url=""):
    err_str = str(e)
    if "404" in err_str: return "Nie znaleziono portalu (Błąd 404).\nSprawdź czy adres URL jest poprawny."
    if "401" in err_str or "403" in err_str: return "Odmowa dostępu (Błąd 401/403).\nTwój MAC może być zablokowany lub wygasł."
    if "500" in err_str or "502" in err_str or "513" in err_str: return f"Błąd serwera dostawcy (Kod {err_str[0:3]}).\nSpróbuj później."
    # Zmieniono 'ConnectTimeout' na ogólne, by wyłapać zamrożenia
    if "timeout" in err_str.lower() or "connection" in err_str.lower(): return "Serwer nie odpowiada (Timeout/Brak połączenia).\nSpróbuj ponownie za chwilę."
    return f"Błąd połączenia:\n{err_str[:100]}..."

def clean_name(name):
    if not name: return "No Name"
    name = str(name).strip()
    name = re.sub(r'^\[.*?\]\s*', '', name)
    name = re.sub(r'^\(.*?\)\s*', '', name)
    name = re.sub(r'^\|.*?\|\s*', '', name)
    name = re.sub(r'^.*?\|\s*', '', name)
    name = re.sub(r'^[A-Z0-9]{2,4}\s?-\s?', '', name)
    return name.strip()

def parse_mac_playlist(host, mac):
    host = host.strip().rstrip('/')

    # 1. Próba Xtream (szybka)
    host_xc = host[:-2] if host.endswith('/c') else host
    url_xc = f"{host_xc}/get.php?username={mac}&password={mac}&type=m3u_plus&output=ts"
    try:
        # Skrócony timeout dla szybkiej próby
        r = requests.get(url_xc, timeout=8, headers={'User-Agent': COMMON_UA}, verify=False)
        if r.status_code == 200 and "#EXTINF" in r.text:
            return parse_m3u_text(r.text)
    except:
        pass

    # 2. Próba Stalker
    if not host.endswith('/c'):
        host_stalker = f"{host}/c"
    else:
        host_stalker = host

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
        
        # Agresywny timeout
        r = s.get(token_url, timeout=10)
        r.raise_for_status()
        js = r.json()
        if not js or "js" not in js or "token" not in js["js"]:
            raise Exception("Brak autoryzacji (Błędny MAC?)")
        token = js["js"]["token"]
        s.headers.update({'Authorization': f'Bearer {token}'})

        # Pobieranie Kategorii
        genres = {}
        try:
            r_g = s.get(f"{host_stalker}/server/load.php?type=itv&action=get_genres&token={token}", timeout=8)
            data_g = r_g.json()
            if "js" in data_g and isinstance(data_g["js"], list):
                for g in data_g["js"]:
                    genres[str(g.get("id"))] = clean_name(g.get("title", "Inne"))
        except:
            pass

        # Pobieranie Kanałów
        s.get(f"{host_stalker}/server/load.php?type=stb&action=get_profile&token={token}", timeout=8)
        # Finalny timeout na listę
        r = s.get(f"{host_stalker}/server/load.php?type=itv&action=get_all_channels&token={token}", timeout=15)
        data = r.json()
        if "js" not in data or "data" not in data["js"]:
            raise Exception("Pusta lista (No JSON).")
        ch_list = data["js"]["data"]
        out = []
        for item in ch_list:
            name_raw = item.get("name", "No Name")
            name = clean_name(name_raw)
            cmd = item.get("cmd", "")
            logo = item.get("logo", "")
            gid = str(item.get("tv_genre_id", ""))
            grp_name = genres.get(gid, "Inne")
            url_clean = cmd.replace("ffmpeg ", "").replace("auto ", "").replace("ch_id=", "")
            if "://" not in url_clean:
                url_clean = f"{host_stalker}/mpegts_to_ts/{url_clean}"
            if logo and not logo.startswith('http'):
                logo = f"{host_stalker}/{logo}"
            out.append({
                "title": name,
                "url": url_clean,
                "group": grp_name,
                "logo": logo,
                "epg": ""
            })
        return out

    except Exception as e:
        friendly_msg = translate_error(e, host_stalker)
        raise Exception(friendly_msg)

def parse_m3u_text(content):
    channels = []
    current_info = {}
    for line in content.splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith('#EXTINF'):
            title = line.rsplit(',', 1)[1].strip() if ',' in line else "No Name"
            logo_m = re.search(r'tvg-logo="([^"]+)"', line)
            logo = logo_m.group(1) if logo_m else ""
            grp_m = re.search(r'group-title="([^"]+)"', line)
            group = grp_m.group(1) if grp_m else "Inne"
            current_info = {"title": clean_name(title), "logo": logo, "group": clean_name(group)}
        elif line.startswith('http') and current_info:
            channels.append({
                "title": current_info["title"],
                "url": current_info["url"],
                "group": current_info["group"],
                "logo": current_info["logo"],
                "epg": ""
            })
            current_info = {}
    return channels

def download_picon_url(url, title):
    if not url: return ""
    safe = re.sub(r'[^\w]', '_', title).strip().lower() + ".png"
    path = f"/usr/share/enigma2/picon/{safe}"
    if os.path.exists(path): return path
    try:
        requests.get(url, timeout=5, verify=False)
        return ""
    except: return ""
