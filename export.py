# -*- coding: utf-8 -*-
import os, re, zlib, urllib.parse
from xml.sax.saxutils import escape
from enigma import eDVBDB

BOUQUET_DIR = "/etc/enigma2"
EPG_CHANNEL_FILE = "/etc/epgimport/iptvdream.channels.xml"

# User-Agent MAG250
RAW_UA = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"

def sanit(name):
    name = str(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    return name.replace(' ', '_') if name else "Unknown"

def sanit_title(name):
    """Agresywne czyszczenie nazw z M3U i Xtream"""
    if not name: return "No Name"
    name = str(name).replace('\n', '').strip()
    
    # 1. Usuwanie technicznych śmieci (tvg-id=, itp.)
    name = re.sub(r'tvg-[a-z]+="[^"]*"', '', name, flags=re.IGNORECASE)
    name = re.sub(r'tvg-[a-z]+=[^\s]+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'group-title="[^"]*"', '', name, flags=re.IGNORECASE)
    name = re.sub(r'group-title=[^\s]+', '', name, flags=re.IGNORECASE)
    
    # 2. Usuwanie nawiasów klamrowych i kwadratowych z zawartością [PL], (VIP)
    name = re.sub(r'[\(\[].*?[\)\]]', '', name)
    
    # 3. Usuwanie prefiksów typu PL|, PL |, PL:
    name = re.sub(r'^(PL|EN|DE|IT|UK|VIP|RAW|FHD|UHD|HEVC|4K)\s*[|:-]?\s*', '', name, flags=re.IGNORECASE)
    
    # 4. Usuwanie sufiksów (końcówek)
    # Lista słów do wycięcia z końca nazwy
    tags = ['HD', 'FHD', 'UHD', '4K', 'RAW', 'VIP', 'PL', 'SD', 'HEVC', 'H265', 'UK', 'US']
    for tag in tags:
        # Usuwa np. " RAW", " - VIP" z końca
        name = re.sub(r'\s+[-|]?\s*' + tag + r'$', '', name, flags=re.IGNORECASE)
    
    # 5. Czyszczenie końcowe
    name = name.replace('|', '').replace(':', '').replace('"', '').strip()
    
    # 6. Jeśli po czyszczeniu pusto (np. kanał nazywał się tylko "VIP"), przywróć oryginał (ale bez śmieci)
    if len(name) < 2: 
        return "Stream"
        
    return name

def export_bouquets(playlist, bouquet_name=None, keep_groups=True, service_type="4097"):
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
            
            # Tutaj też używamy czyszczenia
            title = sanit_title(ch.get("title", "No Name"))
            
            url = url.replace(" ", "%20")
            if "User-Agent" not in url:
                url += ua_suffix
            
            unique_sid = zlib.crc32(url.encode()) & 0xffff
            if unique_sid == 0: unique_sid = 1
            
            ref_str = f"{service_type}:0:1:{unique_sid}:0:0:0:0:0:0:{url}:{title}" 
            content.append(f"#SERVICE {ref_str}\n")
            content.append(f"#DESCRIPTION {title}\n")
            
            sid_hex = f"{unique_sid:X}"
            
            for s_type in ["4097", "5002", "1"]:
                epg_mapping.append((f"{s_type}:0:1:{sid_hex}:0:0:0:0:0:0", title))
            
            total_channels += 1

        with open(bq_fullpath, "w", encoding="utf-8") as f:
            f.write("".join(content))
        
        add_to_bouquets_index(filename)
        total_bouquets += 1

    create_epg_xml(epg_mapping)

    return total_bouquets, total_channels

def add_to_bouquets_index(bq_filename):
    idx = os.path.join(BOUQUET_DIR, "bouquets.tv")
    entry = f'#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{bq_filename}" ORDER BY bouquet\n'
    try:
        lines = []
        if os.path.exists(idx):
            with open(idx, "r", errors="ignore") as f: lines = f.readlines()
        
        if not any(entry.strip() == line.strip() for line in lines):
            lines.append(entry)
            with open(idx, "w") as f: f.writelines(lines)
    except: pass

def create_epg_xml(mapping):
    try:
        os.makedirs("/etc/epgimport", exist_ok=True)
        with open(EPG_CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            visited = set()
            suffixes = ["gb", "uk", "pl", "us", "de", "it", "es", "fr", "nl", "tr", "ug", "tz", "za"]
            for ref, name in mapping:
                if ref in visited: continue
                visited.add(ref)
                clean = name.strip()
                nospace = clean.replace(" ", "")
                kebab = clean.lower().replace(" ", "-")
                ids = set()
                ids.add(escape(clean))
                ids.add(escape(nospace))
                ids.add(escape(kebab))
                for suf in suffixes:
                    ids.add(f"{escape(nospace)}.{suf}")
                    ids.add(f"{escape(kebab)}.{suf}")
                    ids.add(f"{escape(clean)}.{suf}")
                for xid in ids:
                    f.write(f'  <channel id="{xid}">{ref}</channel>\n')
            f.write('</channels>')
    except Exception:
        pass
