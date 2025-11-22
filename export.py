# -*- coding: utf-8 -*-
import os, re, zlib, urllib.parse
from xml.sax.saxutils import escape
from enigma import eDVBDB

BOUQUET_DIR = "/etc/enigma2"
EPG_CHANNEL_FILE = "/etc/epgimport/iptvdream.channels.xml"

# User-Agent MAG250 - Kluczowy dla czarnych ekranów
RAW_UA = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"

def sanit(name):
    name = str(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    return name.replace(' ', '_') if name else "Unknown"

def sanit_title(name):
    """Agresywne czyszczenie nazw"""
    name = str(name).replace('\n', '').strip()
    name = re.sub(r'[\(\[\|\{].*?[\)\]\|\}]\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^\s*(PL\s+VIP|VIP\s+PL|PL|DE|FR|IT|ES|EN|UK|US|USA)\s+', '', name, flags=re.IGNORECASE)
    tags = ['HD', 'FHD', 'UHD', '4K', 'RAW', 'VIP', 'PL', 'SD', 'HEVC', 'H265', 'UK', 'US']
    for tag in tags:
        name = re.sub(r'\s+[-|]?\s*' + tag + r'$', '', name, flags=re.IGNORECASE)
    name = name.replace(':', ' ').replace('"', '').strip()
    return name

def export_bouquets(playlist, bouquet_name=None, keep_groups=True):
    groups = {}
    for ch in playlist:
        grp = ch.get("group", "Main") if keep_groups else "Main"
        groups.setdefault(grp, []).append(ch)

    total_channels = 0
    total_bouquets = 0
    epg_mapping = []

    ua_encoded = urllib.parse.quote(RAW_UA)
    ua_suffix = f"#User-Agent={ua_encoded}"

    for grp, chans in groups.items():
        safe_grp_name = sanit(grp)
        safe_bq_name  = sanit(bouquet_name or "IPTV")
        filename = f"userbouquet.iptv_dream_{safe_bq_name}_{safe_grp_name}.tv".lower()[:60]
        bq_fullpath = os.path.join(BOUQUET_DIR, filename)
        
        content = [f"#NAME {bouquet_name} - {grp}\n"]
        
        for ch in chans:
            url = ch.get("url", "").strip()
            if not url: continue
            
            title = sanit_title(ch.get("title", "No Name"))
            
            # 1. Spacja na %20
            url = url.replace(" ", "%20")
            
            # 2. Dodaj User-Agenta jeśli brak
            if "User-Agent" not in url:
                url += ua_suffix
            
            # 3. CZYSTY LINK (BEZ ZAMIANY : NA %3a) - Ważne dla OpenATV/SF8008
            
            unique_sid = zlib.crc32(url.encode()) & 0xffff
            if unique_sid == 0: unique_sid = 1
            
            service_type = "4097"
            
            ref_str = f"{service_type}:0:1:{unique_sid}:0:0:0:0:0:0:{url}:{title}"
            content.append(f"#SERVICE {ref_str}\n")
            content.append(f"#DESCRIPTION {title}\n")
            
            sid_hex = f"{unique_sid:X}"
            epg_mapping.append((f"4097:0:1:{sid_hex}:0:0:0:0:0:0", title))
            epg_mapping.append((f"1:0:1:{sid_hex}:0:0:0:0:0:0", title))
            
            total_channels += 1

        with open(bq_fullpath, "w", encoding="utf-8") as f:
            f.write("".join(content))
        
        add_to_bouquets_index(filename)
        total_bouquets += 1

    create_epg_xml(epg_mapping)

    try:
        eDVBDB.getInstance().reloadBouquets()
        eDVBDB.getInstance().reloadServicelist()
    except: pass

    return total_bouquets, total_channels

def add_to_bouquets_index(bq_filename):
    idx = os.path.join(BOUQUET_DIR, "bouquets.tv")
    entry = f'#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{bq_filename}" ORDER BY bouquet\n'
    try:
        lines = []
        if os.path.exists(idx):
            with open(idx, "r", errors="ignore") as f: lines = f.readlines()
        if entry not in lines:
            lines.append(entry)
            with open(idx, "w") as f: f.writelines(lines)
    except: pass

def create_epg_xml(mapping):
    """Generator EPG 'Shotgun'"""
    try:
        os.makedirs("/etc/epgimport", exist_ok=True)
        with open(EPG_CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            visited = set()
            
            # Sufiksy krajów zgodne ze źródłami w epg_picon.py
            suffixes = ["gb", "uk", "pl", "us", "de", "it", "es", "fr", "nl", "tr", "ug", "tz", "za"]
            
            for ref, name in mapping:
                if ref in visited: continue
                visited.add(ref)
                
                clean = name.strip()
                nospace = clean.replace(" ", "")
                kebab = clean.lower().replace(" ", "-")
                
                ids = set()
                # Warianty podstawowe
                ids.add(escape(clean))
                ids.add(escape(nospace))
                ids.add(escape(kebab))
                
                # Warianty krajowe
                for suf in suffixes:
                    ids.add(f"{escape(nospace)}.{suf}") # SkySports1.gb
                    ids.add(f"{escape(kebab)}.{suf}")   # sky-sports-1.gb
                    ids.add(f"{escape(clean)}.{suf}")

                for xid in ids:
                    f.write(f'  <channel id="{xid}">{ref}</channel>\n')
            f.write('</channels>')
    except Exception:
        pass
