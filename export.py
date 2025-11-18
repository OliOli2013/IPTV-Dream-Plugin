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
    # Usuwanie śmieci z nazw
    name = re.sub(r'^\[.*?\]\s*', '', name)
    name = re.sub(r'^\(.*?\)\s*', '', name)
    name = re.sub(r'^\|.*?\|\s*', '', name)
    name = re.sub(r'^.*?\|\s*', '', name)
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

            # Generujemy UNIKALNE ID (CRC32) - to jest najlepsze dla EPG
            unique_sid = zlib.crc32(url.encode()) & 0xffff
            if unique_sid == 0: unique_sid = 1
            
            # Typ 4097 (GStreamer)
            service_type = "4097"
            
            # Referencja
            ref_str = f"{service_type}:0:1:{unique_sid}:0:0:0:0:0:0:{url}:{title}"
            
            content.append(f"#SERVICE {ref_str}\n")
            content.append(f"#DESCRIPTION {title}\n")
            
            # Zapisujemy referencję (HEX) i nazwę do mapowania
            ref_hex = f"{unique_sid:X}"
            ref_pure = f"1:0:1:{ref_hex}:0:0:0:0:0:0"
            # Dodajemy też wersję z 4097, bo EPG Import różnie reaguje
            ref_iptv = f"4097:0:1:{ref_hex}:0:0:0:0:0:0"
            
            epg_mapping.append((ref_pure, title))
            epg_mapping.append((ref_iptv, title))
            
            total_channels += 1

        with open(bq_fullpath, "w", encoding="utf-8") as f:
            f.write("".join(content))
            
        add_to_bouquets_index(bq_filename)
        total_bouquets += 1

    # Generujemy plik z aliasami dla EPG Import
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
    """Generuje BARDZO DUŻO aliasów, aby trafić w EPG OVH"""
    try:
        os.makedirs("/etc/epgimport", exist_ok=True)
        with open(EPG_CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            
            seen_refs = set()

            for ref, name in mapping:
                # Unikamy duplikatów referencji w pętli
                if ref in seen_refs: continue
                seen_refs.add(ref)

                name_clean = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                # Lista wariantów nazwy do sprawdzenia w EPG
                aliases = set()
                
                # 1. Oryginał: "TVP 1 HD"
                aliases.add(name_clean)
                
                # 2. Bez spacji: "TVP1HD"
                nospace = name_clean.replace(" ", "")
                aliases.add(nospace)
                
                # 3. Z końcówką .pl: "TVP1HD.pl"
                aliases.add(f"{nospace}.pl")
                
                # 4. Bez HD/FHD/4K/PL
                nohd = re.sub(r'(HD|FHD|UHD|4K|PL)', '', name_clean, flags=re.IGNORECASE).strip()
                aliases.add(nohd)
                
                # 5. Bez HD i bez spacji: "TVP1" (Najczęstszy format w OVH!)
                nohd_nospace = nohd.replace(" ", "")
                aliases.add(nohd_nospace)
                
                # 6. Bez HD, bez spacji + .pl: "TVP1.pl" (Też częste)
                aliases.add(f"{nohd_nospace}.pl")

                # 7. Małymi literami: "tvp1"
                aliases.add(nohd_nospace.lower())
                
                # 8. Małymi + .pl: "tvp1.pl"
                aliases.add(f"{nohd_nospace.lower()}.pl")

                # Zapisujemy wszystkie warianty
                for alias in aliases:
                    if len(alias) > 1: 
                        f.write(f'  <channel id="{alias}">{ref}</channel>\n')
                        
            f.write('</channels>')
    except Exception:
        pass
