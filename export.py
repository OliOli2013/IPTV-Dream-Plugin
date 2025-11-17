# -*- coding: utf-8 -*-
import os, re
from enigma import eDVBDB

BOUQUET_DIR = "/etc/enigma2"

def sanit(name):
    # Bardziej rygorystyczne czyszczenie nazw plików
    # Zamiana polskich znaków i spacji na bezpieczne znaki
    name = str(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = name.replace(' ', '_')
    return name if name else "Unknown"

def sanit_title(name):
    # Dla tytułów wewnątrz pliku (mniej rygorystyczne)
    return str(name).replace('\n', '').strip()

def export_bouquets(playlist, bouquet_name=None, keep_groups=True):
    """
    Zwraca liczbę wyeksportowanych kanałów.
    """
    groups = {}
    for ch in playlist:
        grp = ch.get("group", "Main") if keep_groups else "Main"
        groups.setdefault(grp, []).append(ch)

    total_channels = 0
    
    # Czyścimy stare wpisy w bouquets.tv dotyczące tego pluginu?
    # Tutaj bezpieczniej jest po prostu dodawać nowe.
    
    for grp, chans in groups.items():
        safe_grp_name = sanit(grp)
        safe_bq_name  = sanit(bouquet_name or "IPTV")
        
        # Nazwa pliku bukietu: userbouquet.iptv_dream_nazwagrupy.tv
        filename_core = f"iptv_dream_{safe_bq_name}_{safe_grp_name}".lower()
        # Skracamy jeśli za długa
        if len(filename_core) > 60: filename_core = filename_core[:60]
        
        bq_filename = f"userbouquet.{filename_core}.tv"
        bq_fullpath = os.path.join(BOUQUET_DIR, bq_filename)
        
        display_name = f"{bouquet_name} - {grp}" if keep_groups else bouquet_name

        content = [f"#NAME {display_name}\n"]
        
        for ch in chans:
            url = ch.get("url", "").strip()
            if not url: continue
            
            title = sanit_title(ch.get("title", "No Name"))
            
            # Stream type 5002 (IPTV) jest ok, czasem 4097 jest lepsze dla buforowania
            # Używamy URL encoded space (%20) jeśli są spacje w linku
            url = url.replace(" ", "%20")
            ref = f"5002:0:1:0:0:0:0:0:0:0:{url}:{title}"
            
            content.append(f"#SERVICE {ref}\n")
            content.append(f"#DESCRIPTION {title}\n")
            total_channels += 1

        with open(bq_fullpath, "w", encoding="utf-8") as f:
            f.write("".join(content))
            
        add_to_bouquets_index(bq_filename)

    # Przeładowanie bazy
    try:
        eDVBDB.getInstance().reloadBouquets()
        eDVBDB.getInstance().reloadServicelist()
    except Exception as e:
        print(f"[IPTVDream] Reload failed: {e}")

    return total_channels

def add_to_bouquets_index(bq_filename):
    idx_file = os.path.join(BOUQUET_DIR, "bouquets.tv")
    entry = f'#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{bq_filename}" ORDER BY bouquet\n'
    
    lines = []
    if os.path.exists(idx_file):
        with open(idx_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
    if entry not in lines:
        # Dodajemy przed ostatnim bukietem (często favorites) albo na końcu
        # Bezpieczniej na końcu
        lines.append(entry)
        with open(idx_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
