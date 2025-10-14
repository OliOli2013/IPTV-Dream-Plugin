# -*- coding: utf-8 -*-
import os, re
from enigma import eDVBDB

BOUQUET_DIR = "/etc/enigma2"

def sanit(name):
    return re.sub(r'[^\w\-_. ]', '_', name).strip()

def export_bouquets(playlist, bouquet_name=None, keep_groups=True):
    """Eksportuje playlistę – osobny plik dla każdej grupy."""
    groups = {}
    for ch in playlist:
        grp = ch.get("group", "").strip() if keep_groups else ""
        groups.setdefault(grp, []).append(ch)

    for grp, chans in groups.items():
        name = grp or bouquet_name or "IPTV-Export"   # zachowaj oryginalną nazwę
        safe = sanit(name)
        bq_file = os.path.join(BOUQUET_DIR, f"userbouquet.{safe}.tv")
        with open(bq_file, "w", encoding="utf-8") as f:
            f.write(f"#NAME {name}\n")
            for ch in chans:
                title = sanit(ch.get("title", ""))
                url = ch.get("url", "").strip()
                if not url:
                    continue
                ref = f"5002:0:1:0:0:0:0:0:0:0:{url}:{title}"
                f.write(f"#SERVICE {ref}\n#DESCRIPTION {title}\n")
        add_to_bouquets_tv(os.path.basename(bq_file))

    try:
        eDVBDB.getInstance().reloadBouquets()
    except Exception:
        pass

def add_to_bouquets_tv(bq_filename):
    idx = os.path.join(BOUQUET_DIR, "bouquets.tv")
    marker = f'#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{bq_filename}" ORDER BY bouquet\n'
    if not os.path.exists(idx):
        with open(idx, "w") as f:
            f.write(marker)
    else:
        with open(idx, "r+", encoding="utf-8") as f:
            if bq_filename not in f.read():
                f.seek(0, 2)
                f.write(marker)
