# -*- coding: utf-8 -*-
import os, requests, json, tempfile, shutil

# Zaktualizowane URL dla wersji 5.1
REPO_ZIP      = "https://github.com/OliOli2013/IPTV-Dream-Plugin/archive/refs/heads/main.zip"
CHANGELOG_URL = "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/CHANGELOG.txt"
VERSION_URL   = "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/VERSION"
PLUGIN_DIR    = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"

def _get_local_version():
    """Pobiera lokalną wersję wtyczki."""
    try:
        with open(os.path.join(PLUGIN_DIR, "VERSION"), "r") as f:
            return f.read().strip()
    except:
        return "unknown"

def _get_remote_info():
    """Pobiera informacje o zdalnej wersji i changelog."""
    try:
        # Pobieramy wersję z pliku VERSION
        r_ver = requests.get(VERSION_URL, timeout=5)
        r_ver.raise_for_status()
        remote_ver = r_ver.text.strip()
        
        # Pobieramy changelog
        changelog = ""
        try:
            r_log = requests.get(CHANGELOG_URL, timeout=5)
            if r_log.status_code == 200:
                changelog = r_log.text
        except: pass
            
        return remote_ver, changelog
    except:
        return None, None

def check_update():
    """Sprawdza dostępność aktualizacji."""
    local = _get_local_version()
    remote, changelog = _get_remote_info()
    
    if not remote:
        return False, local, "NETWORK_ERROR", None
    
    if remote != local:
        return True, local, remote, changelog
        
    return False, local, remote, None

def do_update():
    """Wykonuje aktualizację wtyczki."""
    tmp = tempfile.mkdtemp()
    zip_path = os.path.join(tmp, "main.zip")
    SAFE_BAK_DIR = os.path.join(os.path.dirname(PLUGIN_DIR), ".IPTVDream_BAK")
    
    try:
        # Pobranie archiwum z GitHub
        r = requests.get(REPO_ZIP, timeout=30)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            f.write(r.content)
        shutil.unpack_archive(zip_path, tmp)
        
        # Struktura ZIP z GitHuba: IPTV-Dream-Plugin-main/
        extracted_folder = os.path.join(tmp, "IPTV-Dream-Plugin-main")
        
        # Weryfikacja, czy to na pewno pliki wtyczki
        if not os.path.exists(os.path.join(extracted_folder, "plugin.py")):
             # Jeśli nie ma plugin.py w głównym, szukamy w podfolderze
             sub_folder = os.path.join(extracted_folder, "IPTVDream")
             if os.path.isdir(sub_folder) and os.path.exists(os.path.join(sub_folder, "plugin.py")):
                 extracted_folder = sub_folder
             else:
                 raise Exception("Błąd struktury ZIP: Nie znaleziono plugin.py w głównym katalogu.")

        # Instalacja (Bezpieczne przenoszenie)
        if os.path.exists(SAFE_BAK_DIR): 
            shutil.rmtree(SAFE_BAK_DIR)
        
        # Przenosimy obecną wersję do ukrytego backupu
        if os.path.exists(PLUGIN_DIR): 
            shutil.move(PLUGIN_DIR, SAFE_BAK_DIR)
        
        # Przenosimy nową wersję na miejsce
        shutil.move(extracted_folder, PLUGIN_DIR)
        
        # Usuwamy backup
        if os.path.exists(SAFE_BAK_DIR): 
            shutil.rmtree(SAFE_BAK_DIR)

        # Nadajemy uprawnienia
        os.chmod(PLUGIN_DIR, 0o755)
        for r, d, f in os.walk(PLUGIN_DIR):
            for i in d: 
                os.chmod(os.path.join(r, i), 0o755)
            for i in f: 
                os.chmod(os.path.join(r, i), 0o755 if i.endswith(".py") else 0o644)
            
        return True
    except Exception as e:
        # Przywracanie backupu w razie awarii
        if os.path.exists(SAFE_BAK_DIR) and not os.path.exists(PLUGIN_DIR):
             shutil.move(SAFE_BAK_DIR, PLUGIN_DIR)
        raise e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)