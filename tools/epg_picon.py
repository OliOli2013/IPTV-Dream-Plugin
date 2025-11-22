# -*- coding: utf-8 -*-
import os

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

def install_epg_sources():
    try:
        if not os.path.exists(EPG_DIR): os.makedirs(EPG_DIR)
        content = '<?xml version="1.0" encoding="utf-8"?>\n<sources>\n'
        content += '    <sourcecat sourcecatname="IPTV Dream EPG (MEGA)">\n'
        for source in EPG_SOURCES:
            content += f"""        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>{source['description']}</description>
            <url>{source['url']}</url>
        </source>\n"""
        content += '    </sourcecat>\n</sources>\n'
        with open(SOURCE_FILE, "w") as f: f.write(content)
        if not os.path.exists(CHANNEL_FILE):
            with open(CHANNEL_FILE, "w") as f: f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n</channels>')
        return True, "Źródła EPG zaktualizowane."
    except Exception as e:
        return False, f"Błąd: {e}"

def fetch_epg_for_playlist(pl):
    install_epg_sources()

def download_picon_url(url, title):
    return ""
    
create_epg_import_source = install_epg_sources
