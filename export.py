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
    # Agresywne usuwanie śmieci z nazw
    name = re.sub(r'^\[.*?\]\s*', '', name)
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

            # Unikalne ID (SID)
            unique_sid = zlib.crc32(url.encode()) & 0xffff
            if unique_sid == 0: unique_sid = 1
            
            # Typ 4097 (GStreamer)
            service_type = "4097"
            
            # Zapis do bukietu (Dec SID)
            ref_str = f"{service_type}:0:1:{unique_sid}:0:0:0:0:0:0:{url}:{title}"
            content.append(f"#SERVICE {ref_str}\n")
            content.append(f"#DESCRIPTION {title}\n")
            
            # --- MAPOWANIE EPG (Najważniejsza część) ---
            # Generujemy referencję w formacie HEX (takim jak używa Enigma wewnętrznie)
            # Dodajemy wersję z namespace 1 (DVB) oraz 4097 (IPTV), żeby mieć pewność
            sid_hex = f"{unique_sid:X}"
            
            # Wersja 1: Standardowa DVB (najczęściej używana przez EPG Import)
            ref_dvb = f"1:0:1:{sid_hex}:0:0:0:0:0:0"
            
            # Wersja 2: IPTV (dokładna kopia typu serwisu)
            ref_iptv = f"4097:0:1:{sid_hex}:0:0:0:0:0:0"
            
            # Przekazujemy obie do generatora XML
            epg_mapping.append((ref_dvb, title))
            epg_mapping.append((ref_iptv, title))
            
            total_channels += 1

        with open(bq_fullpath, "w", encoding="utf-8") as f:
            f.write("".join(content))
            
        add_to_bouquets_index(bq_filename)
        total_bouquets += 1

    # Generujemy plik XML z aliasami
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
    """Generuje plik z wieloma wariantami nazw (Aliasami)"""
    try:
        os.makedirs("/etc/epgimport", exist_ok=True)
        with open(EPG_CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            
            for ref, name in mapping:
                # Baza: Czysta nazwa
                name_clean = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                # Lista ID do wypróbowania
                ids = set()
                
                # 1. Oryginał: "TVP 1 HD"
                ids.add(name_clean)
                
                # 2. Bez spacji: "TVP1HD"
                nospace = name_clean.replace(" ", "")
                ids.add(nospace)
                
                # 3. Standard OVH (Bez spacji + .pl): "TVP1HD.pl"
                ids.add(f"{nospace}.pl")
                
                # 4. Bez HD i spacji + .pl (Najczęstsze!): "TVP1.pl"
                # Usuwa HD, FHD, UHD, 4K, PL
                nohd = re.sub(r'(HD|FHD|UHD|4K|PL)', '', nospace, flags=re.IGNORECASE)
                ids.add(f"{nohd}.pl")
                
                # 5. Małe litery + .pl: "tvp1.pl"
                ids.add(f"{nohd.lower()}.pl")

                # Zapisz wszystkie warianty dla tej jednej referencji
                for xid in ids:
                    if len(xid) > 2: 
                        f.write(f'  <channel id="{xid}">{ref}</channel>\n')
                        
            f.write('</channels>')
    except Exception:
        pass
