# -*- coding: utf-8 -*-
import os
from ..tools.lang import _ # Dodano import tłumaczeń
from Components.Language import language # Dodano import języka
import requests, re

EPG_URL_KEY = "custom_epg_url" # KLUCZ DO ZAPISYWANIA URL W PROFILU

EPG_SOURCES = [
    # POLSKA
    {"url": "http://epg.ovh/pl.xml.gz", "description": "IPTV Dream - Polska (OVH)"},
    {"url": "https://iptv-epg.org/files/epg-pl.xml.gz", "description": "IPTV Dream - Polska (iptv-epg)"},
    # UK (GB)
    {"url": "https://iptv-epg.org/files/epg-gb.xml.gz", "description": "IPTV Dream - UK (Great Britain)"},
    # USA
    {"url": "https://iptv-epg.org/files/epg-us.xml.gz", "description": "IPTV Dream - USA"},
    # AFRYKA
    {"url": "https://iptv-epg.org/files/epg-ug.xml.gz", "description": "IPTV Dream - Uganda"},
    {"url": "https://iptv-epg.org/files/epg-tz.xml.gz", "description": "IPTV Dream - Tanzania"},
    {"url": "https://iptv-epg.org/files/epg-za.xml.gz", "description": "IPTV Dream - South Africa"},
    # EUROPA
    {"url": "https://iptv-epg.org/files/epg-de.xml.gz", "description": "IPTV Dream - Germany"},
    {"url": "https://iptv-epg.org/files/epg-fr.xml.gz", "description": "IPTV Dream - France"},
    # ŚWIAT
    {"url": "http://epg.bevy.be/bevy.xml.gz", "description": "IPTV Dream - World Mix (Bevy)"}
]

EPG_DIR      = "/etc/epgimport"
SOURCE_FILE  = "/etc/epgimport/iptvdream.sources.xml"
CHANNEL_FILE = "/etc/epgimport/iptvdream.channels.xml"

def install_epg_sources(custom_url=None):
    lang = language.getLanguage()[:2] or "pl"
    try:
        if not os.path.exists(EPG_DIR): os.makedirs(EPG_DIR)
        
        content = '<?xml version="1.0" encoding="utf-8"?>\n<sources>\n'
        content += f'    <sourcecat sourcecatname="{_("epg_dream_sources", lang)}">\n'
        
        # 1. Dodajemy wszystkie źródła domyślne (MEGA)
        for source in EPG_SOURCES:
            content += f"""        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>{source['description']}</description>
            <url>{source['url']}</url>
        </source>\n"""
        
        # 2. Dodajemy własne źródło EPG, jeśli podano
        if custom_url and custom_url.strip().startswith(('http', 'ftp')):
            content += f"""        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>{_("epg_custom", lang)}</description>
            <url>{custom_url.strip()}</url>
        </source>\n"""

        content += '    </sourcecat>\n</sources>\n'
        
        with open(SOURCE_FILE, "w") as f: f.write(content)
        
        # Upewniamy się, że plik mapowania istnieje
        if not os.path.exists(CHANNEL_FILE):
            with open(CHANNEL_FILE, "w") as f: f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n</channels>')
            
        return True, _("epg_updated", lang)
    except Exception as e:
        return False, f"{_('error', lang)}: {e}"

def fetch_epg_for_playlist(pl):
    # Ta funkcja nie musi nic robić, ponieważ główny plik robi to asynchronicznie
    pass

# Zaimplementowana na nowo, zgodnie z oryginalną logiką (ale z requests)
def download_picon_url(url, title):
    if not url: return ""
    # Bezpieczna nazwa pliku (usuwanie znaków specjalnych)
    safe = re.sub(r'[^\w]', '_', title).strip().lower() + ".png"
    path = f"/usr/share/enigma2/picon/{safe}"
    if os.path.exists(path): return path
    try:
        # Pobieranie i zapisywanie (zakładamy, że requests jest zainstalowany)
        r = requests.get(url, timeout=5, verify=False)
        r.raise_for_status()
        with open(path, 'wb') as f:
            f.write(r.content)
        return path
    except: 
        return ""
    
create_epg_import_source = install_epg_sources
