# -*- coding: utf-8 -*-
import os, requests, re, gzip, shutil

# Link użytkownika
EPG_URL      = "https://epg.ovh/pl.xml"
PICON_BASE   = "https://epg.ovh/logo/"

# Ścieżki
EPG_DIR      = "/etc/epgimport"
LOCAL_EPG    = os.path.join(EPG_DIR, "iptvdream.xml") # Plik rozpakowany
SOURCE_FILE  = os.path.join(EPG_DIR, "iptvdream.sources.xml")
CHANNEL_FILE = os.path.join(EPG_DIR, "iptvdream.channels.xml")
PICON_DIR    = "/usr/share/enigma2/picon/"

COMMON_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def create_epg_import_source():
    """Tworzy źródło wskazujące na PLIK LOKALNY"""
    try:
        if not os.path.exists(EPG_DIR):
            os.makedirs(EPG_DIR)

        # Wskazujemy na plik na dysku, a nie URL. To eliminuje błędy pobierania w EPG Import.
        source_content = f"""<?xml version="1.0" encoding="utf-8"?>
<sources>
    <sourcecat sourcecatname="IPTV Dream - Polska">
        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>Polska (EPG.OVH - Lokalny)</description>
            <url>file://{LOCAL_EPG}</url>
        </source>
    </sourcecat>
</sources>
"""
        with open(SOURCE_FILE, "w") as f:
            f.write(source_content)
    except Exception:
        pass

def fetch_epg_for_playlist(pl):
    """Pobiera plik EPG fizycznie na dysk"""
    create_epg_import_source()
    
    try:
        headers = {'User-Agent': COMMON_UA}
        # Pobieramy plik
        r = requests.get(EPG_URL, timeout=60, headers=headers, verify=False, stream=True)
        if r.status_code == 200:
            # Zapisujemy bezpośrednio jako xml (serwer ovh może zwracać xml lub gzip)
            with open(LOCAL_EPG, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
    except Exception:
        pass

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
