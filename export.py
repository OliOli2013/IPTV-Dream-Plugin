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
    
    # 1. Usuwanie technicznych śmieci
    name = re.sub(r'tvg-[a-z]+="[^"]*"', '', name, flags=re.IGNORECASE)
    
    # 2. Usuwanie nawiasów klamrowych i kwadratowych
    name = re.sub(r'[\(\[].*?[\)\]]', '', name)
    
    # 3. Usuwanie prefiksów typu PL|, PL:
    name = re.sub(r'^(PL|EN|DE|IT|UK|VIP|RAW|FHD|UHD|HEVC|4K)\s*[|:-]?\s*', '', name, flags=re.IGNORECASE)
    
    # 4. Usuwanie sufiksów (OSTROŻNIEJ Z XXX)
    tags = ['HD', 'FHD', 'UHD', '4K', 'RAW', 'VIP', 'PL', 'SD', 'HEVC', 'H265', 'UK', 'US']
    for tag in tags:
        # Usuwa np. " RAW", " - VIP" z końca
        name = re.sub(r'\s+[-|]?\s*' + tag + r'$', '', name, flags=re.IGNORECASE)
    
    # 5. Czyszczenie końcowe
    name = name.replace('|', '').replace(':', '').replace('"', '').strip()
    
    if len(name) < 2: 
        return "Stream"
        
    return name

def export_bouquets(playlist, bouquet_name=None, keep_groups=True, service_type="4097"):
    groups = {}
    for ch in playlist:
        # Używamy grupy z playlisty. Jeśli parser M3U działa poprawnie, to tu będą "Movies", "XXX", "PL" itd.
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
            
            title_raw = ch.get("title", "No Name")
            title = sanit_title(title_raw)
            tvg_id = ch.get("epg_id", "")
            
            url = url.replace(" ", "%20")
            if "User-Agent" not in url:
                url += ua_suffix
            
            unique_sid = zlib.crc32(url.encode()) & 0xffff
            if unique_sid == 0: unique_sid = 1
            
            ref_str = f"{service_type}:0:1:{unique_sid}:0:0:0:0:0:0:{url}:{title}" 
            content.append(f"#SERVICE {ref_str}\n")
            content.append(f"#DESCRIPTION {title}\n")
            
            sid_hex = f"{unique_sid:X}"
            
            # Mapowanie EPG dla różnych typów serwisów
            for s_type in ["4097", "5002", "1"]:
                # Przekazujemy krotkę (ServiceRef, CleanName, TVG-ID)
                epg_mapping.append((f"{s_type}:0:1:{sid_hex}:0:0:0:0:0:0", title, tvg_id))
            
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

# --- ULEPSZONY GENERATOR EPG (WIĘCEJ DOPASOWAŃ) ---
def create_epg_xml(mapping):
    try:
        os.makedirs("/etc/epgimport", exist_ok=True)
        with open(EPG_CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            visited = set()
            suffixes = ["gb", "uk", "pl", "us", "de", "it", "es", "fr", "nl", "tr", "ug", "tz", "za"]
            
            # Mapping to lista krotek: (ServiceRef, CleanName, TvgID)
            for entry in mapping:
                if len(entry) == 3:
                    ref, name, tvg = entry
                else:
                    ref, name = entry
                    tvg = ""
                    
                if ref in visited: continue
                visited.add(ref)
                
                clean = name.strip()
                nospace = clean.replace(" ", "")
                kebab = clean.lower().replace(" ", "-")
                
                # Zbiór wszystkich ID, które przypiszemy do tego kanału
                ids = set()
                
                # 1. PRIORYTET: TVG-ID z pliku M3U
                if tvg:
                    ids.add(escape(tvg))
                
                # 2. Nazwa czysta
                ids.add(escape(clean))
                ids.add(escape(nospace))
                
                # 3. Kombinacje z sufiksami krajowymi (np. Polsat.pl)
                for suf in suffixes:
                    ids.add(f"{escape(nospace)}.{suf}")
                    ids.add(f"{escape(kebab)}.{suf}")
                    ids.add(f"{escape(clean)}.{suf}")
                
                # 4. Dodatkowe wariacje (np. usunięcie 'HD' z nazwy dla lepszego dopasowania)
                # Często w XMLTV jest "TVP 1", a kanał to "TVP 1 FHD"
                simple_name = re.sub(r'(HD|FHD|UHD|4K|RAW|VIP|PL|TV)', '', clean, flags=re.IGNORECASE).strip()
                if simple_name and len(simple_name) > 2:
                     simple_nospace = simple_name.replace(" ", "")
                     ids.add(escape(simple_name))
                     for suf in suffixes:
                         ids.add(f"{escape(simple_nospace)}.{suf}")

                # 5. Wariacje dla kanałów z numerami (np. TVP 1, TVP1, TVP-1)
                num_match = re.search(r'(\d+)$', clean)
                if num_match:
                    num = num_match.group(1)
                    prefix = clean[:num_match.start()].strip()
                    # Wersja bez spacji przed numerem
                    nospace_version = prefix + num
                    ids.add(escape(nospace_version))
                    # Wersja z myślnikiem
                    dash_version = prefix + "-" + num
                    ids.add(escape(dash_version))
                    # Wersja z kropką
                    dot_version = prefix + "." + num
                    ids.add(escape(dot_version))
                    
                    # Kombinacje z sufiksami
                    for suf in suffixes:
                        ids.add(f"{escape(nospace_version)}.{suf}")
                        ids.add(f"{escape(dash_version)}.{suf}")

                # 6. Wariacje dla stacji międzynarodowych
                intl_patterns = [
                    f"{escape(clean)}HD",
                    f"{escape(clean)}FHD", 
                    f"{escape(clean)}UHD",
                    f"{escape(clean)}4K",
                    f"{escape(clean)}TV",
                    f"{escape(clean)}CHANNEL",
                    f"{escape(nospace)}HD",
                    f"{escape(nospace)}TV"
                ]
                for pattern in intl_patterns:
                    ids.add(pattern)
                    for suf in suffixes:
                        ids.add(f"{pattern}.{suf}")

                # 7. Dla kanałów XXX - specjalne wariacje
                if 'xxx' in clean.lower() or 'adult' in clean.lower():
                    ids.add("xxx")
                    ids.add("adult")
                    ids.add("xxx.tv")
                    ids.add("adult.tv")

                # 8. Dla kanałów VOD - specjalne wariacje
                if 'vod' in clean.lower() or 'movie' in clean.lower():
                    ids.add("vod")
                    ids.add("movies")
                    ids.add("vod.tv")
                    ids.add("movies.tv")

                # Zapisujemy wszystkie warianty dla danego ServiceRef
                for xid in ids:
                    f.write(f'  <channel id="{xid}">{ref}</channel>\n')
                    
            f.write('</channels>')
    except Exception as e:
        print(f"[IPTVDream] Błąd EPG XML: {e}")