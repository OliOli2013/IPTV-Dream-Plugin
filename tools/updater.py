# -*- coding: utf-8 -*-
import os, requests, json, tempfile, shutil

REPO_ZIP      = "https://github.com/OliOli2013/IPTV-Dream-Plugin/archive/refs/heads/main.zip"
VERSION_URL   = "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/VERSION"
CHANGELOG_URL = "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/CHANGELOG.txt"
PLUGIN_DIR    = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"

def _get_local_version():
    try:
        with open(os.path.join(PLUGIN_DIR, "VERSION"), "r") as f:
            return f.read().strip()
    except:
        return "Brak (Pierwsza instalacja)"

def _get_remote_info():
    """Pobiera wersję i changelog z GitHuba"""
    try:
        # 1. Pobierz numer wersji
        r_ver = requests.get(VERSION_URL, timeout=5)
        r_ver.raise_for_status()
        remote_ver = r_ver.text.strip()
        
        # 2. Pobierz changelog (opcjonalnie)
        changelog = ""
        try:
            r_log = requests.get(CHANGELOG_URL, timeout=5)
            if r_log.status_code == 200:
                changelog = r_log.text
        except:
            changelog = "Brak listy zmian."
            
        return remote_ver, changelog
    except:
        return None, None

def check_update():
    local = _get_local_version()
    remote, changelog = _get_remote_info()
    
    if not remote:
        return False, local, "Błąd połączenia"
        
    # Proste porównanie stringów (można rozbudować o semver)
    if remote != local:
        # Zwracamy: CzyNowa, Lokalna, Zdalna, Changelog
        return True, local, remote, changelog
        
    return False, local, remote, None

def do_update():
    tmp = tempfile.mkdtemp()
    zip_path = os.path.join(tmp, "main.zip")
    
    SAFE_BAK_DIR = os.path.join(os.path.dirname(PLUGIN_DIR), ".IPTVDream_BAK")
    
    try:
        r = requests.get(REPO_ZIP, timeout=30)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            f.write(r.content)
        shutil.unpack_archive(zip_path, tmp)
        
        main_folder = "IPTV-Dream-Plugin-main"
        src = os.path.join(tmp, main_folder, "IPTVDream") # Struktura płaska (jak teraz)
        
        if not os.path.isdir(src):
             # Fallback dla starej struktury
             src = os.path.join(tmp, main_folder, "enigma2-plugin", "Extensions", "IPTVDream")
             if not os.path.isdir(src):
                  # Fallback dla struktury root (jeśli pliki są luzem w main)
                  # To wymaga, żebyś miał folder IPTVDream w repo, ale jeśli masz pliki luzem,
                  # to instalator musi je zebrać. Zakładamy strukturę z folderem IPTVDream.
                  raise Exception("Nieprawidłowa struktura pliku ZIP")

        # Kopiowanie pliku VERSION i CHANGELOG do wtyczki, żeby były lokalnie
        try:
            shutil.copy(os.path.join(tmp, main_folder, "VERSION"), os.path.join(src, "VERSION"))
        except: pass

        if os.path.exists(SAFE_BAK_DIR): shutil.rmtree(SAFE_BAK_DIR)
        if os.path.exists(PLUGIN_DIR): shutil.move(PLUGIN_DIR, SAFE_BAK_DIR)
        
        shutil.move(src, PLUGIN_DIR)
        
        if os.path.exists(SAFE_BAK_DIR): shutil.rmtree(SAFE_BAK_DIR)

        os.chmod(PLUGIN_DIR, 0o755)
        for r, d, f in os.walk(PLUGIN_DIR):
            for i in d: os.chmod(os.path.join(r, i), 0o755)
            for i in f: os.chmod(os.path.join(r, i), 0o755 if i.endswith(".py") else 0o644)
            
        return True
    except Exception as e:
        if os.path.exists(SAFE_BAK_DIR) and not os.path.exists(PLUGIN_DIR):
             shutil.move(SAFE_BAK_DIR, PLUGIN_DIR)
        raise e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
