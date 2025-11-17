# -*- coding: utf-8 -*-
import json, os, requests, re
from datetime import datetime

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

def parse_mac_playlist(host, mac):
    # --- POPRAWKA GŁÓWNA: Usuwamy ukośnik na końcu hosta ---
    # Jeśli użytkownik wpisze "http://.../c/", funkcja zmieni to na "http://.../c"
    host = host.strip().rstrip('/')

    url = f"{host}/player_api.php?username={mac}&password={mac}&action=get_live_streams"
    
    try:
        # verify=False jest ważne dla starszych dekoderów z nieaktualnym SSL
        r = requests.get(url, timeout=15, verify=False)
        r.raise_for_status()
        
        data = r.json()
        
        # Jeśli API zwróci słownik (błąd) zamiast listy, obsłuż to
        if isinstance(data, dict) and "user_info" not in data: 
             # Czasami API zwraca pusty słownik lub błąd w innej formie
             pass 

        # Używamy .get() dla bezpieczeństwa (gdyby brakowało klucza 'name' lub 'stream_url')
        return [{
            "title": ch.get("name", "Bez nazwy"), 
            "url": ch.get("stream_url", ""), 
            "epg": "", 
            "logo": ch.get("stream_icon", "")
        } for ch in data if isinstance(ch, dict)]

    except Exception as e:
        raise Exception(f"Błąd MAC: {str(e)}")

def download_picon_url(url, title):
    if not url:
        return ""
    
    # Bezpieczniejsza nazwa pliku
    safe = re.sub(r'[^\w]', '_', title).strip().lower() + ".png"
    path = f"/usr/share/enigma2/picon/{safe}"
    
    if os.path.exists(path):
        return path
        
    try:
        r = requests.get(url, timeout=10, verify=False)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    except Exception:
        return ""
