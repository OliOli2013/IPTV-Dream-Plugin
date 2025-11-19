# -*- coding: utf-8 -*-
import os, re, zlib, urllib.parse
from enigma import eDVBDB

BOUQUET_DIR = "/etc/enigma2"
EPG_CHANNEL_FILE = "/etc/epgimport/iptvdream.channels.xml"
# Zmieniony User-Agent na mniej specyficzny/starszy (częściej akceptowany przez portale)
RAW_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
# Dodanie domyślnego Referer, który często stabilizuje odtwarzanie (np. dla HLS)
DEFAULT_REFERER = "http://localhost" 

def sanit(name):
    name = str(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    return name.replace(' ', '_') if name else "Unknown"

def sanit_title(name):
    name = str(name).replace('\n', '').strip()
    
    # 1. Usuń przedrostki w nawiasach/kwadratach/klamrach
    name = re.sub(r'[\(\[\|\{].*?[\)\]\|\}]\s*|^\s*[\(\[\|\{](PL|DE|FR|IT|ES|EN|CZ|SK|HU|UA|TR|RO)[\)\]\|\}]\s*', '', name, flags=re.IGNORECASE)
    
    # 2. Usuń konkretne problematyczne przedrostki z początku nazwy:
    name = re.sub(r'^\s*(PL\s+VIP|VIP\s+PL)\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^\s*(PL|DE|FR|IT|ES|EN|CZ|SK|HU|UA|TR|RO)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^\s*([A-Z]{2,4}\s?-\s?|\d+\s?-\s?|TV\s?-\s?)', '', name, flags=re.IGNORECASE) 
    
    # 3. Usuń powtarzające się sufiksy (HD, RAW, 4K, VIP, itp.)
    TAGS_TO_REMOVE = r'(HD|FHD|UHD|4K|RAW|PL|VIP|DE|FR|IT|ES|EN|GR|BG|CZ|SK|HU|UA|TR|RO|\d+H|TEST|\d+P|SD|FHD|TVP|TTV)'
    
    name = re.sub(r'\s+[\-\+\s]*%s$' % TAGS_TO_REMOVE, '', name, flags=re.IGNORECASE)
    name = re.sub(r'%s$' % TAGS_TO_REMOVE, '', name, flags=re.IGNORECASE)
    
    # 4. Dodatkowe czyszczenie i podwójne spacje
    name = name.replace(':', '').replace('"', '').replace('|', '').replace('-', ' ').strip()
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

def export_bouquets(playlist, bouquet_name=None, keep_groups=True):
    groups = {}
    for ch in playlist:
        grp = ch.get("group", "Main") if keep_groups else "Main"
        groups.setdefault(grp, []).append(ch)

    total_channels = 0
    total_bouquets = 0
    epg_mapping = []

    # Kodowanie User-Agenta i Referer dla ServiceApp
    ua_encoded = urllib.parse.quote(RAW_UA)
    referer_encoded = urllib.parse.quote(DEFAULT_REFERER) # Dodanie Referer
    
    # UZUPELNIONY SUFIX O REFERER (poprawny format dla Enigmy to #param1=val1&param2=val2...)
    ua_suffix = f"#User-Agent={ua_encoded}&Referer={referer_encoded}" 

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
            
            # Dodajemy nagłówki, jeśli nie ma ich w URL
            if "User-Agent" not in url and "#User-Agent" not in url:
                url += ua_suffix
            
            url = url.replace(" ", "%20")
            
            # Unikalne ID (SID)
            unique_sid = zlib.crc32(url.encode()) & 0xffff
            if unique_sid == 0: unique_sid = 1
            
            # Typ 4097 (GStreamer)
            service_type = "4097"
            
            ref_str = f"{service_type}:0:1:{unique_sid}:0:0:0:0:0:0:{url}:{title}"
            content.append(f"#SERVICE {ref_str}\n")
            content.append(f"#DESCRIPTION {title}\n")
            
            # Referencje do mapy EPG (jak poprzednio)
            sid_hex = f"{unique_sid:X}"
            ref_pure = f"1:0:1:{sid_hex}:0:0:0:0:0:0"
            ref_iptv = f"4097:0:1:{sid_hex}:0:0:0:0:0:0"
            
            epg_mapping.append((ref_pure, title))
            epg_mapping.append((ref_iptv, title))
            
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
    lines = []
    if os.path.exists(idx):
        with open(idx, "r", errors="ignore") as f: lines = f.readlines()
    if entry not in lines:
        lines.append(entry)
        with open(idx, "w") as f: f.writelines(lines)

def create_epg_xml(mapping):
    """Generuje plik z wieloma wariantami nazw (Aliasami) - wersja użytkownika"""
    try:
        os.makedirs("/etc/epgimport", exist_ok=True)
        with open(EPG_CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            
            visited_refs = set()

            for ref, name in mapping:
                if ref in visited_refs: continue
                visited_refs.add(ref)

                name_clean = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                ids = set()

                ids.add(name_clean)
                nospace = name_clean.replace(" ", "")
                ids.add(nospace)
                ids.add(f"{nospace}.pl")
                ids.add(f"{nospace.lower()}.pl")
                
                nohd = re.sub(r'(HD|FHD|UHD|4K|PL|VIP)', '', nospace, flags=re.IGNORECASE)
                if nohd != nospace:
                    ids.add(f"{nohd}.pl")

                for xid in ids:
                    if len(xid) > 2:
                        f.write(f'  <channel id="{xid}">{ref}</channel>\n')
                        
            f.write('</channels>')
    except Exception:
        pass
