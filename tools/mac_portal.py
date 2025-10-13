# -*- coding: utf-8 -*-
import json, os, requests, re
from datetime import datetime

MAC_FILE = "/etc/enigma2/iptvdream_mac.json"

def load_mac_json():
    try:
        with open(MAC_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_mac_json(data):
    with open(MAC_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def parse_mac_playlist(host, mac):
    url = f"{host}/player_api.php?username={mac}&password={mac}&action=get_live_streams"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return [{"title": ch["name"], "url": ch["stream_url"], "epg": "", "logo": ch.get("stream_icon", "")} for ch in r.json()]
    except Exception as e:
        raise Exception("Błąd MAC: " + str(e))

def download_picon_url(url, title):
    if not url:
        return ""
    safe = re.sub(r'\W+', '_', title).lower() + ".png"
    path = f"/usr/share/enigma2/picon/{safe}"
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
