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
    # 1. Czyszczenie wstępne (spacje i slash na końcu)
    host = host.strip().rstrip('/')

    # 2. FIX: Usuwanie końcówki "/c" (częsty błąd przy portalach Stalker/MAG)
    # Adres API zazwyczaj leży w katalogu głównym, a nie w /c/
    if host.endswith('/c'):
        host = host[:-2] # Usuwa ostatnie 2 znaki

    # 3. Ponowne czyszczenie slasha na wszelki wypadek
    host = host.rstrip('/')

    url = f"{host}/player_api.php?username={mac}&password={mac}&action=get_live_streams"
    
    try:
        # verify=False - kluczowe dla starszych dekoderów i certyfikatów
        r = requests.get(url, timeout=15, verify=False)
        r.raise_for_status()
        
        data = r.json()
        
        # Zabezpieczenie przed sytuacją, gdy API zwraca błąd jako słownik bez kluczy kanałów
        if isinstance(data, dict) and "user_info" not in data: 
             pass 

        # Parsowanie wyników na listę kanałów
        return [{
            "title": ch.get("name", "Bez nazwy"), 
            "url": ch.get("stream_url", ""), 
            "epg": "", 
            "logo": ch.get("stream_icon", "")
        } for ch in data if isinstance(ch, dict)]

    except Exception as e:
        # W treści błędu zwracamy też URL, żeby łatwiej diagnozować
        raise Exception(f"Błąd MAC: {str(e)} | URL: {url}")

def download_picon_url(url, title):
    if not url:
        return ""
    # Bezpieczna nazwa pliku
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
