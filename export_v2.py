# -*- coding: utf-8 -*-
"""
ULEPSZONY MODUŁ EKSPORTU I EPG v5.1
- Zintegrowane z nowym systemem EPG
- Lepsze dopasowanie do kanałów satelitarnych
- Rozszerzone mapowanie EPG
"""

import os, re, zlib, urllib.parse, json, requests
from xml.sax.saxutils import escape
from enigma import eDVBDB

BOUQUET_DIR = "/etc/enigma2"
EPG_CHANNEL_FILE = "/etc/epgimport/iptvdream.channels.xml"

# User-Agent MAG250
RAW_UA = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"

def sanit(name):
    """Czyści nazwę dla systemu plików."""
    name = str(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    return name.replace(' ', '_') if name else "Unknown"

def sanit_title(name):
    """Agresywne czyszczenie nazw z M3U i Xtream."""
    if not name: 
        return "No Name"
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
        name = re.sub(r'\s+[-|]?\s*' + tag + r'$', '', name, flags=re.IGNORECASE)
    
    # 5. Czyszczenie końcowe
    name = name.replace('|', '').replace(':', '').replace('"', '').strip()
    
    if len(name) < 2: 
        return "Stream"
        
    return name

def get_satellite_channel_ref(channel_name):
    """
    NOWA FUNKCJA: Zwraca referencję kanału satelitarnego na podstawie nazwy
    """
    # Mapowanie popularnych kanałów do referencji satelitarnych
    SAT_CHANNELS = {
        'tvp1': '1:0:19:6FF:2F:1:0:0:0:0:',
        'tvp2': '1:0:19:700:2F:1:0:0:0:0:',
        'polsat': '1:0:19:1E2C:1:1:0:0:0:0:',
        'tvn': '1:0:19:1E2D:1:1:0:0:0:0:',
        'polsatnews': '1:0:19:1E2E:1:1:0:0:0:0:',
        'tvpsport': '1:0:19:1E2F:1:1:0:0:0:0:',
        'hbo': '1:0:19:1E30:1:1:0:0:0:0:',
        'hbo2': '1:0:19:1E31:1:1:0:0:0:0:',
        'axn': '1:0:19:1E32:1:1:0:0:0:0:',
        'fox': '1:0:19:1E33:1:1:0:0:0:0:',
        'discovery': '1:0:19:1E34:1:1:0:0:0:0:',
        'animalplanet': '1:0:19:1E35:1:1:0:0:0:0:',
        'tlc': '1:0:19:1E36:1:1:0:0:0:0:',
        'mtv': '1:0:19:1E37:1:1:0:0:0:0:',
        'cnn': '1:0:19:1E38:1:1:0:0:0:0:',
        'bbc': '1:0:19:1E39:1:1:0:0:0:0:',
        'deutschland': '1:0:19:1E3A:1:1:0:0:0:0:',
        'rtl': '1:0:19:1E3B:1:1:0:0:0:0:',
        'prosieben': '1:0:19:1E3C:1:1:0:0:0:0:',
        'sky': '1:0:19:1E3D:1:1:0:0:0:0:',
    }
    
    # Czyszczenie nazwy
    clean_name = re.sub(r'[^a-z0-9]', '', channel_name.lower())
    
    # Szukanie dopasowania
    for sat_name, ref in SAT_CHANNELS.items():
        if sat_name in clean_name:
            return ref
    
    return None

def export_bouquets(playlist, bouquet_name=None, keep_groups=True, service_type="4097"):
    """Eksportuje playlistę do bukietów Enigma 2."""
    groups = {}
    for ch in playlist:
        grp = ch.get("group", "Main") if keep_groups else "Main"
        groups.setdefault(grp, []).append(ch)

    total_channels = 0
    total_bouquets = 0
    epg_mapping = []

    ua_encoded = urllib.parse.quote(RAW_UA)
    ua_suffix = f"#User-Agent={ua_encoded}"

    def _mk_bouquet_filename(bq_name, group_name):
        """Create a collision-resistant bouquet filename.

        Wcześniej plik był obcinany do 60 znaków, co przy długich nazwach (np. MAC-...)
        ucinało część z nazwą grupy i powodowało nadpisywanie wielu bukietów jednym plikiem.
        """
        safe_bq = sanit(bq_name or "IPTV")
        safe_grp = sanit(group_name or "Main")
        # Krótkie segmenty + hash gwarantują unikalność.
        sig = zlib.crc32((safe_bq + "|" + safe_grp).encode("utf-8", "ignore")) & 0xffffffff
        safe_bq_s = safe_bq[:28]
        safe_grp_s = safe_grp[:28]
        fn = "userbouquet.iptv_dream_%s_%s_%08x.tv" % (safe_bq_s, safe_grp_s, sig)
        return fn.lower()

    for grp, chans in groups.items():
        filename = _mk_bouquet_filename(bouquet_name, grp)
        bq_fullpath = os.path.join(BOUQUET_DIR, filename)

        # Zapis strumieniowy: nie trzymaj tysięcy linii w pamięci.
        with open(bq_fullpath, "w", encoding="utf-8") as f:
            f.write("#NAME %s - %s\n" % (bouquet_name or "IPTV", grp))

            for ch in chans:
                url = (ch.get("url", "") or "").strip()
                if not url:
                    continue

                title_raw = ch.get("title", "No Name")
                title = sanit_title(title_raw)
                tvg_id = ch.get("epg_id", "")

                url = url.replace(" ", "%20")
                if "User-Agent" not in url:
                    url += ua_suffix

                unique_sid = zlib.crc32(url.encode()) & 0xffff
                if unique_sid == 0:
                    unique_sid = 1

                # Sprawdzamy czy mamy referencję satelitarną
                sat_ref = get_satellite_channel_ref(title)
                if sat_ref:
                    ref_str = f"{service_type}:0:1:{unique_sid}:0:0:0:0:0:0:{url}:{title}"
                    f.write(f"#SERVICE {ref_str}\n")
                    f.write(f"#DESCRIPTION {title}\n")
                    epg_mapping.append((sat_ref, title, title))
                else:
                    ref_str = f"{service_type}:0:1:{unique_sid}:0:0:0:0:0:0:{url}:{title}"
                    f.write(f"#SERVICE {ref_str}\n")
                    f.write(f"#DESCRIPTION {title}\n")

                    sid_hex = f"{unique_sid:X}"
                    for s_type in ["4097", "5002", "1"]:
                        epg_mapping.append((f"{s_type}:0:1:{sid_hex}:0:0:0:0:0:0", title, tvg_id))

                total_channels += 1

        add_to_bouquets_index(filename)
        total_bouquets += 1

    create_epg_xml(epg_mapping)

    return total_bouquets, total_channels

def add_to_bouquets_index(bq_filename):
    """Dodaje bukiet do indeksu."""
    idx = os.path.join(BOUQUET_DIR, "bouquets.tv")
    entry = f'#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{bq_filename}" ORDER BY bouquet\n'
    try:
        lines = []
        if os.path.exists(idx):
            with open(idx, "r", errors="ignore") as f: 
                lines = f.readlines()
        
        if not any(entry.strip() == line.strip() for line in lines):
            lines.append(entry)
            with open(idx, "w") as f: 
                f.writelines(lines)
    except: 
        pass

def create_epg_xml(mapping):
    """
    ULEPSZONY GENERATOR EPG (Z MAPOWANIEM DO KANAŁÓW SATELITARNYCH)
    """
    try:
        os.makedirs("/etc/epgimport", exist_ok=True)
        with open(EPG_CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            visited = set()
            
            # Rozszerzone sufiksy
            suffixes = ["gb", "uk", "pl", "us", "de", "it", "es", "fr", "nl", "tr", "ug", "tz", "za", "eu", "world"]
            
            for entry in mapping:
                if len(entry) == 3:
                    ref, name, tvg = entry
                else:
                    ref, name = entry
                    tvg = ""
                    
                if ref in visited: 
                    continue
                visited.add(ref)
                
                clean = name.strip()
                nospace = clean.replace(" ", "")
                kebab = clean.lower().replace(" ", "-")
                
                # Zbiór wszystkich ID
                ids = set()
                
                # 1. PRIORYTET: TVG-ID z pliku M3U
                if tvg:
                    ids.add(escape(tvg))
                
                # 2. Nazwa czysta
                ids.add(escape(clean))
                ids.add(escape(nospace))
                
                # 3. Kombinacje z sufiksami krajowymi
                for suf in suffixes:
                    ids.add(f"{escape(nospace)}.{suf}")
                    ids.add(f"{escape(kebab)}.{suf}")
                    ids.add(f"{escape(clean)}.{suf}")
                
                # 4. Wersja uproszczona
                simple_name = re.sub(r'(HD|FHD|UHD|4K|RAW|VIP|PL|TV)', '', clean, flags=re.IGNORECASE).strip()
                if simple_name and len(simple_name) > 2:
                     simple_nospace = simple_name.replace(" ", "")
                     ids.add(escape(simple_name))
                     for suf in suffixes:
                         ids.add(f"{escape(simple_nospace)}.{suf}")

                # 5. Wersje z numerami
                num_match = re.search(r'(\d+)$', clean)
                if num_match:
                    num = num_match.group(1)
                    prefix = clean[:num_match.start()].strip()
                    nospace_version = prefix + num
                    dash_version = prefix + "-" + num
                    dot_version = prefix + "." + num
                    
                    ids.add(escape(nospace_version))
                    ids.add(escape(dash_version))
                    ids.add(escape(dot_version))
                    
                    for suf in suffixes:
                        ids.add(f"{escape(nospace_version)}.{suf}")
                        ids.add(f"{escape(dash_version)}.{suf}")

                # 6. Wersje międzynarodowe
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

                # 7. Dla kanałów XXX
                if 'xxx' in clean.lower() or 'adult' in clean.lower():
                    ids.add("xxx")
                    ids.add("adult")
                    ids.add("xxx.tv")
                    ids.add("adult.tv")

                # 8. Dla kanałów VOD
                if 'vod' in clean.lower() or 'movie' in clean.lower():
                    ids.add("vod")
                    ids.add("movies")
                    ids.add("vod.tv")
                    ids.add("movies.tv")

                # 9. Dla kanałów sportowych
                sport_keywords = ['sport', 'espn', 'sky sport', 'bt sport', 'eurosport']
                for keyword in sport_keywords:
                    if keyword in clean.lower():
                        ids.add(f"sport_{keyword.replace(' ', '_')}")
                        ids.add(f"{keyword.replace(' ', '_')}.tv")

                # Zapisujemy wszystkie warianty
                for xid in ids:
                    f.write(f'  <channel id="{xid}">{ref}</channel>\n')
                    
            f.write('</channels>')
    except Exception as e:
        print(f"[IPTVDream] Błąd EPG XML: {e}")

def create_satellite_epg_mapping():
    """
    NOWA FUNKCJA: Tworzy mapowanie EPG dla kanałów satelitarnych
    """
    try:
        # Lista referencji kanałów satelitarnych
        sat_refs = {
            'tvp1': '1:0:19:6FF:2F:1:0:0:0:0:',
            'tvp2': '1:0:19:700:2F:1:0:0:0:0:',
            'polsat': '1:0:19:1E2C:1:1:0:0:0:0:',
            'tvn': '1:0:19:1E2D:1:1:0:0:0:0:',
            'hbo': '1:0:19:1E30:1:1:0:0:0:0:',
            'axn': '1:0:19:1E32:1:1:0:0:0:0:',
        }
        
        with open(EPG_CHANNEL_FILE, "a", encoding="utf-8") as f:
            for name, ref in sat_refs.items():
                f.write(f'  <channel id="{name}">{ref}</channel>\n')
                f.write(f'  <channel id="{name}.pl">{ref}</channel>\n')
                f.write(f'  <channel id="{name}_pl">{ref}</channel>\n')
                
    except Exception as e:
        print(f"[IPTVDream] Błąd mapowania EPG satelitarnego: {e}")

def export_epg_to_m3u(playlist, filename="/tmp/iptvdream_with_epg.m3u"):
    """
    NOWA FUNKCJA: Eksportuje playlistę M3U z dodanymi informacjami EPG
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            
            for channel in playlist:
                title = channel.get('title', 'No Name')
                url = channel.get('url', '')
                group = channel.get('group', 'Inne')
                logo = channel.get('logo', '')
                epg_id = channel.get('epg_id', '')
                
                # Budujemy linię EXTINF z informacjami EPG
                extinf = f'#EXTINF:-1'
                
                if group:
                    extinf += f' group-title="{group}"'
                if logo:
                    extinf += f' tvg-logo="{logo}"'
                if epg_id:
                    extinf += f' tvg-id="{epg_id}"'
                
                extinf += f',{title}\n'
                
                f.write(extinf)
                f.write(f"{url}\n")
        
        return filename
    except Exception as e:
        print(f"[IPTVDream] Błąd eksportu M3U z EPG: {e}")
        return None

# Nowa wersja funkcji create_epg_import_source
create_epg_import_source_with_mapping = create_epg_xml