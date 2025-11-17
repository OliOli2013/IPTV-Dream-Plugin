# -*- coding: utf-8 -*-
import os, re, zlib, urllib.parse
from enigma import eDVBDB

BOUQUET_DIR = "/etc/enigma2"
EPG_CHANNEL_FILE = "/etc/epgimport/iptvdream.channels.xml"

# User-Agent identyczny jak przy pobieraniu (Stalker/Xtream)
# Używamy długiego UA, bo taki jest często wymagany przez zabezpieczenia
RAW_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

def sanit(name):
    name = str(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = name.replace(' ', '_')
    return name if name else "Unknown"

def sanit_title(name):
    name = str(name).replace('\n', '').strip()
    # Agresywne czyszczenie: usuwa wszystko przed znakiem | (np. PL-VIP|)
    name = re.sub(r'^.*?\|\s*', '', name)
    # Usuwa dwukropki i inne znaki psujące nazwy
    name = name.replace(':', '').replace('"', '')
    return name.strip()

def export_bouquets(playlist, bouquet_name=None, keep_groups=True):
    groups = {}
    for ch in playlist:
        grp = ch.get("group", "Main") if keep_groups else "Main"
        groups.setdefault(grp, []).append(ch)

    total_channels = 0
    total_bouquets = 0
    epg_mapping = []

    # KODOWANIE URL (FIX):
    # Spacje w User-Agent muszą być zamienione na %20, inaczej Enigma utnie link.
    # Używamy quote() tylko na wartości UA.
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
            
            # 1. Czysta nazwa
            title = sanit_title(ch.get("title", "No Name"))
            
            # 2. Poprawa URL (zamiana spacji na %20 w samym linku)
            url = url.replace(" ", "%20")
            
            # 3. Dodanie User-Agenta (jeśli go nie ma)
            if "User-Agent" not in url:
                url += ua_suffix

            # 4. Unikalne ID (SID) dla EPG
            unique_sid = zlib.crc32(url.encode()) & 0xffff
            if unique_sid == 0: unique_sid = 1
            
            # 5. TYP 4097 (GStreamer) - STABILNOŚĆ
            # 5002 (Exteplayer3) powoduje zwiechy przy błędach strumienia.
            # 4097 jest bezpieczniejszy.
            service_type = "4097"
            
            # 6. Budowa referencji
            # Format: Typ:0:1:SID:0:0:0:0:0:0:URL:NAZWA
            ref_str = f"{service_type}:0:1:{unique_sid}:0:0:0:0:0:0:{url}:{title}"
            
            content.append(f"#SERVICE {ref_str}\n")
            content.append(f"#DESCRIPTION {title}\n")
            
            # Mapowanie dla EPG Import
            # Zapisujemy ID w HEX (szesnastkowo), bo tak lubi Enigma
            ref_pure = f"1:0:1:{unique_sid:X}:0:0:0:0:0:0"
            epg_mapping.append((ref_pure, title))
            
            total_channels += 1

        with open(bq_fullpath, "w", encoding="utf-8") as f:
            f.write("".join(content))
            
        add_to_bouquets_index(bq_filename)
        total_bouquets += 1

    # Generowanie pliku XML dla EPG
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
    try:
        os.makedirs("/etc/epgimport", exist_ok=True)
        with open(EPG_CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            for ref, name in mapping:
                # Czyścimy nazwę do ID (XML nie lubi spacji w ID, ale EPG Import to przełknie)
                # Ważne: escape znaków specjalnych
                name_esc = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                f.write(f'  <channel id="{name_esc}">{ref}</channel>\n')
            f.write('</channels>')
    except Exception:
        pass
