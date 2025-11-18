# -*- coding: utf-8 -*-
import os, re, zlib, urllib.parse
from enigma import eDVBDB

BOUQUET_DIR = "/etc/enigma2"
EPG_CHANNEL_FILE = "/etc/epgimport/iptvdream.channels.xml"

RAW_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

def sanit(name):
    name = str(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = name.replace(' ', '_')
    return name if name else "Unknown"

def sanit_title(name):
    name = str(name).replace('\n', '').strip()
    # 1. Usuwamy [XX]
    name = re.sub(r'^\[.*?\]\s*', '', name)
    # 2. Usuwamy |XX|
    name = re.sub(r'^\|.*?\|\s*', '', name)
    # 3. Usuwamy XXX|
    name = re.sub(r'^.*?\|\s*', '', name)
    # 4. Usuwamy XX - 
    name = re.sub(r'^[A-Z0-9]{2,4}\s?-\s?', '', name)
    
    name = name.replace(':', '').replace('"', '').strip()
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
        
        filename_core = f"iptv_dream_{safe_bq_name}_{safe_grp_name}".lower()[:60]
        bq_filename = f"userbouquet.{filename_core}.tv"
        bq_fullpath = os.path.join(BOUQUET_DIR, bq_filename)
        
        display_name = f"{bouquet_name} - {grp}" if keep_groups else bouquet_name
        content = [f"#NAME {display_name}\n"]
        
        for ch in chans:
            url = ch.get("url", "").strip()
            if not url: continue
            
            title = sanit_title(ch.get("title", "No Name"))
            url = url.replace(" ", "%20")
            
            if "User-Agent" not in url:
                url += ua_suffix

            unique_sid = zlib.crc32(url.encode()) & 0xffff
            if unique_sid == 0: unique_sid = 1
            
            service_type = "4097"
            ref_str = f"{service_type}:0:1:{unique_sid}:0:0:0:0:0:0:{url}:{title}"
            
            content.append(f"#SERVICE {ref_str}\n")
            content.append(f"#DESCRIPTION {title}\n")
            
            # Mapowanie EPG
            ref_pure = f"1:0:1:{unique_sid:X}:0:0:0:0:0:0"
            epg_mapping.append((ref_pure, title))
            
            total_channels += 1

        with open(bq_fullpath, "w", encoding="utf-8") as f:
            f.write("".join(content))
            
        add_to_bouquets_index(bq_filename)
        total_bouquets += 1

    create_epg_xml(epg_mapping)

    try:
        eDVBDB.getInstance().reloadBouquets()
        eDVBDB.getInstance().reloadServicelist()
    except Exception:
        pass

    return total_bouquets, total_channels

def add_to_bouquets_index(bq_filename):
    idx_file = os.path.join(BOUQUET_DIR, "bouquets.tv")
    entry = f'#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{bq_filename}" ORDER BY bouquet\n'
    lines = []
    if os.path.exists(idx_file):
        with open(idx_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    if entry not in lines:
        lines.append(entry)
        with open(idx_file, "w", encoding="utf-8") as f:
            f.writelines(lines)

def create_epg_xml(mapping):
    """Generuje MULTI-ALIAS dla EPG Import"""
    try:
        os.makedirs("/etc/epgimport", exist_ok=True)
        with open(EPG_CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            
            for ref, name in mapping:
                # Przygotowanie bazy
                name_clean = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                # Zbiór ID do wygenerowania dla tego jednego kanału
                ids_to_generate = set()
                
                # 1. Oryginał: "TVP ABC"
                ids_to_generate.add(name_clean)
                
                # 2. Bez spacji: "TVPABC"
                nospace = name_clean.replace(" ", "")
                ids_to_generate.add(nospace)
                
                # 3. Wersja z .pl (standard OVH): "TVPABC.pl"
                ids_to_generate.add(f"{nospace}.pl")
                
                # 4. Bez końcówki HD/FHD: "TVP ABC" (jeśli było TVP ABC HD)
                nohd = re.sub(r'\s(HD|FHD|UHD|4K)', '', name_clean, flags=re.IGNORECASE).strip()
                if nohd != name_clean:
                    ids_to_generate.add(nohd)
                    # I wersja bez spacji bez HD: "TVPABC"
                    ids_to_generate.add(nohd.replace(" ", ""))

                # Zapisujemy wszystkie warianty dla tej samej referencji
                for eid in ids_to_generate:
                    if len(eid) > 1: # Ignorujemy puste/krótkie
                        f.write(f'  <channel id="{eid}">{ref}</channel>\n')
                        
            f.write('</channels>')
    except Exception:
        pass
