# -*- coding: utf-8 -*-
import os, requests, re

# Używamy HTTP, bo jest pewniejsze na starszych dekoderach w EPG Import
EPG_URL      = "http://epg.ovh/pl.xml"
PICON_BASE   = "http://epg.ovh/logo/"

EPG_DIR      = "/etc/epgimport"
SOURCE_FILE  = os.path.join(EPG_DIR, "iptvdream.sources.xml")
CHANNEL_FILE = os.path.join(EPG_DIR, "iptvdream.channels.xml")
PICON_DIR    = "/usr/share/enigma2/picon/"

COMMON_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def create_epg_import_source():
    """Tworzy plik źródła widoczny w EPG Import"""
    try:
        if not os.path.exists(EPG_DIR):
            os.makedirs(EPG_DIR)

        # Wskazujemy na kanały generowane przez export.py oraz URL online
        source_content = f"""<?xml version="1.0" encoding="utf-8"?>
<sources>
    <sourcecat sourcecatname="IPTV Dream - Polska">
        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>Polska (EPG.OVH - Online)</description>
            <url>{EPG_URL}</url>
        </source>
    </sourcecat>
</sources>
"""
        with open(SOURCE_FILE, "w") as f:
            f.write(source_content)
            
        # Tworzymy pusty plik kanałów, jeśli go nie ma (żeby EPG Import nie krzyczał błędem)
        if not os.path.exists(CHANNEL_FILE):
            with open(CHANNEL_FILE, "w") as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n</channels>')
                
    except Exception:
        pass

def fetch_epg_for_playlist(pl):
    """Uruchamia się po pobraniu listy"""
    create_epg_import_source()
    # Nie pobieramy tu pliku XML ręcznie, zostawiamy to wtyczce EPG Import

def download_picon_url(url, title):
    if not url: return ""
    safe_filename = re.sub(r'[^\w]', '_', title).strip().lower() + ".png"
    path = os.path.join(PICON_DIR, safe_filename)
    if os.path.exists(path): return path
        
    headers = {'User-Agent': COMMON_UA}
    
    # 1. Próba oryginalna
    try:
        r = requests.get(url, timeout=10, headers=headers, verify=False)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except: pass

    # 2. Próba z OVH
    try:
        clean_name = title.replace(" ", "").replace("-", "")
        ovh_url = f"{PICON_BASE}{clean_name}.png"
        r = requests.get(ovh_url, timeout=5, headers=headers, verify=False)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except: pass
    return ""
