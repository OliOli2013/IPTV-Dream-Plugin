# -*- coding: utf-8 -*-
import os, requests, json, tempfile, shutil

REPO_ZIP   = "https://github.com/OliOli2013/IPTV-Dream-Plugin/archive/refs/heads/main.zip"
PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"

def _get_local_version():
    try:
        with open(os.path.join(PLUGIN_DIR, "VERSION"), "r") as f: return f.read().strip()
    except: return "unknown"

def _get_remote_version():
    try:
        r = requests.get("https://api.github.com/repos/OliOli2013/IPTV-Dream-Plugin/commits?per_page=1", timeout=10)
        r.raise_for_status()
        return r.json()[0]["commit"]["committer"]["date"][:10]
    except: return None

def check_update():
    local, remote = _get_local_version(), _get_remote_version()
    if not remote: return False, local, "error"
    return (remote != local), local, remote

def do_update():
    tmp = tempfile.mkdtemp()
    try:
        r = requests.get(REPO_ZIP, timeout=30)
        with open(os.path.join(tmp, "main.zip"), "wb") as f: f.write(r.content)
        shutil.unpack_archive(os.path.join(tmp, "main.zip"), tmp)
        
        src = os.path.join(tmp, "IPTV-Dream-Plugin-main", "IPTVDream")
        if not os.path.isdir(src):
            src = os.path.join(tmp, "IPTV-Dream-Plugin-main", "enigma2-plugin", "Extensions", "IPTVDream")
            if not os.path.isdir(src): raise Exception("bad structure")

        bak = PLUGIN_DIR + ".bak_hidden"
        if os.path.exists(bak): shutil.rmtree(bak)
        if os.path.exists(PLUGIN_DIR): shutil.move(PLUGIN_DIR, bak)
        shutil.move(src, PLUGIN_DIR)
        if os.path.exists(bak): shutil.rmtree(bak)

        os.chmod(PLUGIN_DIR, 0o755)
        for r, d, f in os.walk(PLUGIN_DIR):
            for i in d: os.chmod(os.path.join(r, i), 0o755)
            for i in f: os.chmod(os.path.join(r, i), 0o755 if i.endswith(".py") else 0o644)
            
        with open(os.path.join(PLUGIN_DIR, "VERSION"), "w") as v: v.write(_get_remote_version())
        return True
    except Exception as e:
        if os.path.exists(bak) and not os.path.exists(PLUGIN_DIR): shutil.move(bak, PLUGIN_DIR)
        raise e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
