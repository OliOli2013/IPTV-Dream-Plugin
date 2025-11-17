# -*- coding: utf-8 -*-
import os, re
from enigma import eDVBDB

BOUQUET_DIR = "/etc/enigma2"

def sanit(name):
    name = str(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = name.replace(' ', '_')
    return name if name else "Unknown"

def sanit_title(name):
    return str(name).replace('\n', '').replace(':', '').strip()

def export_bouquets(playlist, bouquet_name=None, keep_groups=True):
    groups = {}
    for ch in playlist:
        grp = ch.get("group", "Main") if keep_groups else "Main"
        groups.setdefault(grp, []).append(ch)

    total_channels = 0
    total_bouquets = 0

    # ZMIANA 1: Uproszczony User-Agent (bez spacji), aby nie psuł parsowania listy
    # Używamy Mozilla/5.0, bo to najbardziej uniwersalny "fałszywy dowód"
    ua_suffix = "#User-Agent=Mozilla/5.0"

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
            
            # Dodajemy User-Agent jeśli go nie ma
            if "#User-Agent" not in url:
                url += ua_suffix

            # ZMIANA 2: Wymuszenie typu 5002 (Exteplayer3)
            # 4097 = GStreamer (często nie działa z IPTV Stalker)
            # 5002 = Exteplayer3 (wymaga ServiceApp, ale działa najlepiej)
            service_type = "5002" 
            
            ref = f"{service_type}:0:1:0:0:0:0:0:0:0:{url}:{title}"
            
            content.append(f"#SERVICE {ref}\n")
            content.append(f"#DESCRIPTION {title}\n")
            total_channels += 1

        with open(bq_fullpath, "w", encoding="utf-8") as f:
            f.write("".join(content))
            
        add_to_bouquets_index(bq_filename)
        total_bouquets += 1

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
