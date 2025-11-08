# -*- coding: utf-8 -*-
import os, requests, re
from .lang import _

EPG_URL      = "https://cyfrowypolsat.eu/epg/epg.xml.gz"
EPG_FILE     = "/etc/epgimport/iptvdream.xml.gz"
PICON_DIR    = "/usr/share/enigma2/picon/"

def fetch_epg_for_playlist(pl):
    try:
        os.makedirs("/etc/epgimport", exist_ok=True)
        r = requests.get(EPG_URL, timeout=30)
        r.raise_for_status()
        with open(EPG_FILE, "wb") as f:
            f.write(r.content)
        for ch in pl:
            ch["epg"] = "iptvdream.xml.gz"
    except Exception:
        pass

def download_picon_url(url, title):
    if not url:
        return ""
    safe = re.sub(r'\W+', '_', title).lower() + ".png"
    path = os.path.join(PICON_DIR, safe)
    if os.path.exists(path):
        return path
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    except Exception:
        return ""
