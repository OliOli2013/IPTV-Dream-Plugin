# -*- coding: utf-8 -*-
import os

# Pewny link do polskiego EPG
EPG_URL = "http://epg.ovh/pl.xml.gz"

# Ścieżki - ZMIANA NAZWY PLIKU, aby uniknąć konfliktów
EPG_DIR      = "/etc/epgimport"
# Nowa nazwa pliku źródła:
SOURCE_FILE  = "/etc/epgimport/iptvdream_fix.sources.xml"
CHANNEL_FILE = "/etc/epgimport/iptvdream.channels.xml"

def create_epg_import_source():
    """Tworzy unikalny plik źródła dla EPG Import"""
    try:
        if not os.path.exists(EPG_DIR):
            os.makedirs(EPG_DIR)

        # Treść pliku źródła z UNIKALNĄ nazwą kategorii
        source_content = f"""<?xml version="1.0" encoding="utf-8"?>
<sources>
    <sourcecat sourcecatname="IPTV Dream (NAPRAWIONE)">
        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>Polska (EPG OVH)</description>
            <url>{EPG_URL}</url>
        </source>
    </sourcecat>
</sources>
"""
        # Zapisujemy plik źródła
        with open(SOURCE_FILE, "w") as f:
            f.write(source_content)
            
        # Upewniamy się, że plik kanałów też istnieje
        if not os.path.exists(CHANNEL_FILE):
            with open(CHANNEL_FILE, "w") as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n</channels>')
                
    except Exception as e:
        print(f"[IPTVDream] Błąd zapisu: {e}")

def fetch_epg_for_playlist(pl):
    """Uruchamiane przy pobieraniu listy"""
    create_epg_import_source()

def download_picon_url(url, title):
    return ""
