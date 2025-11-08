# -*- coding: utf-8 -*-
import os, json, urllib.request, urllib.error, shutil, subprocess

UPDATE_URL = "https://msisystem.t.pl/iptvdream/version.json"
PLUGIN_ROOT = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"

def check_update():
    try:
        with urllib.request.urlopen(UPDATE_URL, timeout=5) as f:
            rem = json.load(f)
        remote_ver = rem.get("version", "0")
    except Exception:
        remote_ver = "0"

    local_ver = "2.3"  # taka sama jak PLUGIN_VERSION w dream.py
    return remote_ver > local_ver, local_ver, remote_ver

def do_update():
    try:
        tmp = "/tmp/iptvdream_update.tar.gz"
        urllib.request.urlretrieve(UPDATE_URL.replace("version.json", "iptvdream.tar.gz"), tmp)
        shutil.rmtree(f"{PLUGIN_ROOT}.old", ignore_errors=True)
        shutil.move(PLUGIN_ROOT, f"{PLUGIN_ROOT}.old")
        subprocess.check_call(["tar", "-xzf", tmp, "-C", os.path.dirname(PLUGIN_ROOT)])
        os.remove(tmp)
        return True
    except Exception as e:
        shutil.rmtree(PLUGIN_ROOT, ignore_errors=True)
        shutil.move(f"{PLUGIN_ROOT}.old", PLUGIN_ROOT)
        raise e
