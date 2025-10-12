# -*- coding: utf-8 -*-
import os, re
from enigma import eDVBDB

BOUQUET_DIR = "/etc/enigma2"

def sanit(name):
    return re.sub(r'[^\w\-_. ]', '_', name).strip()

def export_bouquets(playlist, bouquet_name="IPTV-Export"):
    safe_name = sanit(bouquet_name)
    bq_file = os.path.join(BOUQUET_DIR, "userbouquet.%s.tv" % safe_name)
    with open(bq_file, "w", encoding="utf-8") as f:
        f.write("#NAME %s\n" % bouquet_name)
        for idx, item in enumerate(playlist, start=1):
            title = sanit(item.get("title") or "") or "Channel-%d" % idx
            url = (item.get("url") or "").strip()
            if not url:
                continue
            ref = "5002:0:1:0:0:0:0:0:0:0:%s:%s" % (url, title)
            f.write("#SERVICE %s\n" % ref)
            f.write("#DESCRIPTION %s\n" % title)
    add_to_bouquets_tv(os.path.basename(bq_file))
    try:
        eDVBDB.getInstance().reloadBouquets()
    except Exception:
        pass

def add_to_bouquets_tv(bq_filename):
    idx_path = os.path.join(BOUQUET_DIR, "bouquets.tv")
    marker = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet\n' % bq_filename
    if not os.path.exists(idx_path):
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(marker)
    else:
        with open(idx_path, "r+", encoding="utf-8") as f:
            content = f.read()
            if bq_filename not in content:
                f.seek(0, 2)
                f.write(marker)
