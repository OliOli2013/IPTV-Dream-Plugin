# -*- coding: utf-8 -*-
import os, json, re, urllib.request, urllib.error

MAC_FILE = "/etc/enigma2/iptvdream_mac.json"

def load_mac_json():
    try:
        with open(MAC_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_mac_json(data):
    with open(MAC_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def parse_mac_playlist(host, mac):
    """Prosty parser MAC-portalu – zwraca listę kanałów."""
    mac = mac.upper().replace("-", ":")
    url = f"{host}/get.php?mac={mac}&type=m3u_plus&output=ts"
    req = urllib.request.Request(url, headers={"User-Agent": "IPTVDream/2.3"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP {e.code}")
    except Exception as e:
        raise Exception(str(e))

    from ..dream import parse_m3u_bytes_improved
    return parse_m3u_bytes_improved(data)
