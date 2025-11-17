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

# --- GENEROWANIE LOSOWEGO SERIAL NUMBER (wymagane przez niektóre portale) ---
def get_random_sn():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=13))

def parse_mac_playlist(host, mac):
    # 1. Czyszczenie adresu
    host = host.strip().rstrip('/')
    
    # Jeśli użytkownik NIE podał /c, a serwer to Stalker, dodajmy /c do bazy
    # Ale najpierw sprawdźmy proste metody.
    
    # --- METODA 1: Xtream Codes (Standardowa) ---
    # Dla serwerów, które pozwalają na get.php
    # Spróbujmy bez /c/ jeśli tam jest
    host_xc = host[:-2] if host.endswith('/c') else host
    url_xc = f"{host_xc}/get.php?username={mac}&password={mac}&type=m3u_plus&output=ts"
    
    try:
        headers_xc = {'User-Agent': 'VLC/3.0.20 LibVLC/3.0.20'}
        r = requests.get(url_xc, timeout=10, headers=headers_xc, verify=False)
        if r.status_code == 200 and "#EXTINF" in r.text:
            return parse_m3u_text(r.text)
    except:
        pass # Błąd? Idziemy do Metody 2 (Stalker)

    # --- METODA 2: STALKER MIDDLEWARE (Dla błędu 513/404) ---
    # Wymaga hosta z końcówką /c/ (zazwyczaj)
    if not host.endswith('/c'):
        host_stalker = f"{host}/c"
    else:
        host_stalker = host

    # Przygotowanie sesji
    s = requests.Session()
    s.verify = False
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3',
        'Referer': f"{host_stalker}/",
        'Accept': '*/*',
        'Cookie': f'mac={mac}; stb_lang=en; timezone=Europe/London;'
    })

    try:
        # KROK A: Handshake (Pobranie tokena)
        # Generujemy losowy Serial Number, bo niektóre serwery blokują puste
        sn = get_random_sn()
        token_url = f"{host_stalker}/server/load.php?type=stb&action=handshake&token=&mac={mac}&stb_type=MAG250&ver=ImageDescription: 0.2.18-r14-250; ImageDate: Fri Jan 15 15:20:44 EET 2016; PORTAL version: 5.1.0; API Version: JS API version: 328; STB API version: 134;&sn={sn}"
        
        r = s.get(token_url, timeout=15)
        r.raise_for_status()
        js = r.json()
        
        if not js or "js" not in js or "token" not in js["js"]:
             raise Exception(f"Błąd Handshake: Serwer nie dał tokena. Odpowiedź: {str(js)}")
             
        token = js["js"]["token"]
        
        # Aktualizacja nagłówków o token (Bearer)
        s.headers.update({'Authorization': f'Bearer {token}'})

        # KROK B: Pobranie profilu (opcjonalne, ale czasem wymagane, żeby "aktywować" sesję)
        s.get(f"{host_stalker}/server/load.php?type=stb&action=get_profile&token={token}", timeout=10)

        # KROK C: Pobranie listy wszystkich kanałów
        channels_url = f"{host_stalker}/server/load.php?type=itv&action=get_all_channels&token={token}"
        r = s.get(channels_url, timeout=20)
        r.raise_for_status()
        
        data = r.json()
        if "js" not in data or "data" not in data["js"]:
             raise Exception("Błąd Stalkera: Nie znaleziono listy kanałów w odpowiedzi.")
             
        ch_list = data["js"]["data"]
        
        # Parsowanie specyficznego formatu Stalkera na nasz format
        out = []
        for item in ch_list:
            name = item.get("name", "No Name")
            cmd  = item.get("cmd", "")
            logo = item.get("logo", "")
            
            # URL w Stalkerze często wygląda tak: "ffmpeg http://..." lub "auto http://..."
            # Musimy wyciągnąć czysty link http
            url_clean = cmd.replace("ffmpeg ", "").replace("auto ", "").replace("ch_id=", "")
            
            # Jeśli link nie jest pełnym adresem http, musimy go zbudować (rzadki przypadek)
            if "://" not in url_clean:
                 # Czasem to tylko ID kanału, co wymagałoby create_link.php... 
                 # Ale spróbujmy najprostszego playera
                 url_clean = f"{host_stalker}/mpegts_to_ts/{url_clean}"

            # Jeśli logo jest ścieżką względną
            if logo and not logo.startswith('http'):
                logo = f"{host_stalker}/{logo}"

            out.append({
                "title": name,
                "url":   url_clean,
                "group": "Stalker", # Stalker API get_all_channels rzadko zwraca grupy w tym samym zapytaniu
                "logo":  logo,
                "epg":   ""
            })
            
        if not out:
            raise Exception("Lista kanałów Stalker jest pusta.")
            
        return out

    except Exception as e:
        # Jeśli Stalker zawiedzie, rzuć błąd z opisem
        raise Exception(f"Błąd Połączenia (Stalker/Xtream): {str(e)}")

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
