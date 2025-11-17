# -*- coding: utf-8 -*-
import os, requests, re

# URL do EPG (Domyślny Polski). 
# Jeśli Twój dostawca IPTV daje własny link EPG, podmień go tutaj!
EPG_URL      = "https://cyfrowypolsat.eu/epg/epg.xml.gz"

# Ścieżki dla EPG Import
EPG_DIR      = "/etc/epgimport"
EPG_FILE     = os.path.join(EPG_DIR, "iptvdream.xml.gz")
SOURCE_FILE  = os.path.join(EPG_DIR, "iptvdream.sources.xml")
CHANNEL_FILE = os.path.join(EPG_DIR, "iptvdream.channels.xml") # Wymagany przez EPG Import, nawet pusty

PICON_DIR    = "/usr/share/enigma2/picon/"

def create_epg_import_source():
    """Tworzy plik konfiguracyjny, aby EPG Import widział nasze EPG"""
    if not os.path.exists(EPG_DIR):
        try: os.makedirs(EPG_DIR)
        except: return

    # 1. Tworzymy plik sources.xml
    source_content = """<?xml version="1.0" encoding="utf-8"?>
<sources>
    <sourcecat sourcecatname="IPTV Dream">
        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>IPTV Dream EPG (Pobranie)</description>
            <url>{}</url>
        </source>
    </sourcecat>
</sources>
""".format(EPG_FILE) # Wskazujemy na plik lokalny, który pobierzemy

    try:
        with open(SOURCE_FILE, "w") as f:
            f.write(source_content)
            
        # 2. Tworzymy pusty plik channels.xml (wymagany przez strukturę EPG Import)
        if not os.path.exists(CHANNEL_FILE):
            with open(CHANNEL_FILE, "w") as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n</channels>')
    except Exception:
        pass

def fetch_epg_for_playlist(pl):
    """Pobiera plik EPG i zapisuje go lokalnie"""
    create_epg_import_source()
    
    try:
        # Udajemy przeglądarkę
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(EPG_URL, timeout=30, headers=headers, verify=False)
        r.raise_for_status()
        
        with open(EPG_FILE, "wb") as f:
            f.write(r.content)
            
        # Opcjonalnie: Przypisz nazwę pliku do playlisty (choć EPG Import działa niezależnie)
        for ch in pl:
            ch["epg"] = "iptvdream.xml.gz"
    except Exception:
        pass

def download_picon_url(url, title):
    """Pobiera piconę (logo) kanału"""
    if not url:
        return ""
        
    # Bezpieczna nazwa pliku (bez spacji i znaków specjalnych)
    safe = re.sub(r'[^\w]', '_', title).strip().lower() + ".png"
    path = os.path.join(PICON_DIR, safe)
    
    if os.path.exists(path):
        return path
        
    try:
        # Dodano User-Agent i verify=False (FIX dla blokowanych picon)
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, timeout=10, headers=headers, verify=False)
        r.raise_for_status()
        
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    except Exception:
        return ""
