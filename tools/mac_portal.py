# -*- coding: utf-8 -*-
import json, os, requests, re, random, string

MAC_FILE = "/etc/enigma2/iptvdream_mac.json"

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

def parse_mac_playlist(host, mac):
    host = host.strip().rstrip('/')
    
    # --- METODA 1: Xtream Codes (M3U) ---
    host_xc = host[:-2] if host.endswith('/c') else host
    url_xc = f"{host_xc}/get.php?username={mac}&password={mac}&type=m3u_plus&output=ts"
    
    try:
        headers_xc = {'User-Agent': 'VLC/3.0.20 LibVLC/3.0.20'}
        r = requests.get(url_xc, timeout=10, headers=headers_xc, verify=False)
        if r.status_code == 200 and "#EXTINF" in r.text:
            return parse_m3u_text(r.text)
    except:
        pass 

    # --- METODA 2: STALKER (Z Kategoriami) ---
    if not host.endswith('/c'):
        host_stalker = f"{host}/c"
    else:
        host_stalker = host

    s = requests.Session()
    s.verify = False
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3',
        'Referer': f"{host_stalker}/",
        'Cookie': f'mac={mac}; stb_lang=en; timezone=Europe/London;'
    })

    try:
        # 1. Handshake
        sn = get_random_sn()
        token_url = f"{host_stalker}/server/load.php?type=stb&action=handshake&token=&mac={mac}&stb_type=MAG250&ver=ImageDescription: 0.2.18-r14-250; ImageDate: Fri Jan 15 15:20:44 EET 2016; PORTAL version: 5.1.0; API Version: JS API version: 328; STB API version: 134;&sn={sn}"
        
        r = s.get(token_url, timeout=15)
        r.raise_for_status()
        js = r.json()
        
        if not js or "js" not in js or "token" not in js["js"]:
             raise Exception(f"Błąd Handshake: {str(js)}")
             
        token = js["js"]["token"]
        s.headers.update({'Authorization': f'Bearer {token}'})

        # 2. Pobranie Kategorii (Genres) - NOWOŚĆ
        genres = {}
        try:
            r_g = s.get(f"{host_stalker}/server/load.php?type=itv&action=get_genres&token={token}", timeout=10)
            data_g = r_g.json()
            if "js" in data_g and isinstance(data_g["js"], list):
                for g in data_g["js"]:
                    gid = g.get("id")
                    title = g.get("title", "Inne")
                    if gid:
                        genres[gid] = title
        except:
            pass # Jeśli się nie uda pobrać kategorii, trudno

        # 3. Pobranie Kanałów
        s.get(f"{host_stalker}/server/load.php?type=stb&action=get_profile&token={token}", timeout=10)
        
        channels_url = f"{host_stalker}/server/load.php?type=itv&action=get_all_channels&token={token}"
        r = s.get(channels_url, timeout=20)
        r.raise_for_status()
        
        data = r.json()
        if "js" not in data or "data" not in data["js"]:
             raise Exception("Błąd Stalkera: Pusta lista.")
             
        ch_list = data["js"]["data"]
        
        out = []
        for item in ch_list:
            name = item.get("name", "No Name")
            cmd  = item.get("cmd", "")
            logo = item.get("logo", "")
            gid  = item.get("tv_genre_id") # ID Kategorii
            
            # Przypisanie nazwy grupy na podstawie ID
            grp_name = genres.get(gid, "Stalker Inne")
            # Jeśli ID jest stringiem, spróbujmy int
            if grp_name == "Stalker Inne":
                try: grp_name = genres.get(int(gid), "Stalker Inne")
                except: pass

            url_clean = cmd.replace("ffmpeg ", "").replace("auto ", "").replace("ch_id=", "")
            if "://" not in url_clean:
                 url_clean = f"{host_stalker}/mpegts_to_ts/{url_clean}"

            if logo and not logo.startswith('http'):
                logo = f"{host_stalker}/{logo}"

            out.append({
                "title": name,
                "url":   url_clean,
                "group": grp_name, # Tutaj wstawiamy prawdziwą grupę!
                "logo":  logo,
                "epg":   ""
            })
            
        return out

    except Exception as e:
        raise Exception(f"Błąd Stalker: {str(e)}")

def parse_m3u_text(content):
    channels = []
    current_info = {}
    for line in content.splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith('#EXTINF'):
            title_match = line.rsplit(',', 1)
            title = title_match[1].strip() if len(title_match) > 1 else "Bez nazwy"
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            logo = logo_match.group(1) if logo_match else ""
            group_match = re.search(r'group-title="([^"]+)"', line)
            group = group_match.group(1) if group_match else "Inne"
            current_info = {"title": title, "logo": logo, "group": group}
        elif line.startswith('http') and current_info:
            channels.append({
                "title": current_info["title"],
                "url":   line,
                "group": current_info["group"],
                "logo":  current_info["logo"],
                "epg":   ""
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
