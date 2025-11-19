# -*- coding: utf-8 -*-
import os, requests, json, tempfile, shutil

REPO_ZIP   = "https://github.com/OliOli2013/IPTV-Dream-Plugin/archive/refs/heads/main.zip"
PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"

def _get_local_version():
    # ... (kod bez zmian) ...
    """wersja = data commitu zapisana w pliku VERSION"""
    try:
        with open(os.path.join(PLUGIN_DIR, "VERSION"), "r") as f:
            return f.read().strip()
    except Exception:
        return "unknown"

def _get_remote_version():
    # ... (kod bez zmian) ...
    """pobiera datę ostatniego commitu z API GitHub"""
    try:
        api = "https://api.github.com/repos/OliOli2013/IPTV-Dream-Plugin/commits?per_page=1"
        r = requests.get(api, timeout=10)
        r.raise_for_status()
        return r.json()[0]["commit"]["committer"]["date"][:10]   # YYYY-MM-DD
    except Exception:
        return None

def check_update():
    # ... (kod bez zmian) ...
    local  = _get_local_version()
    remote = _get_remote_version()
    if not remote:
        return False, local, "network error"
    if remote != local:
        return True, local, remote
    return False, local, remote        # brak nowej wersji

def do_update():
    """ściąga i rozpakowuje (wywoływane TYLKO po potwierdzeniu)"""
    tmp = tempfile.mkdtemp()
    zip_path = os.path.join(tmp, "main.zip")
    
    # ZMIENNA DLA BACKUPU: Nazwa nie może zawierać .bak na końcu
    SAFE_BAK_DIR = os.path.join(os.path.dirname(PLUGIN_DIR), ".IPTVDream_BAK")
    
    try:
        r = requests.get(REPO_ZIP, timeout=30)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            f.write(r.content)
        shutil.unpack_archive(zip_path, tmp)
        
        # Logika wyboru ścieżki
        main_folder_name = "IPTV-Dream-Plugin-main"
        src = os.path.join(tmp, main_folder_name, "IPTVDream")
        
        if not os.path.isdir(src):
            src = os.path.join(tmp, main_folder_name, "enigma2-plugin", "Extensions", "IPTVDream")
            if not os.path.isdir(src):
                raise Exception("bad archive structure")

        # backup & replace: Zabezpieczamy się przed skanerem Enigmy2
        if os.path.exists(SAFE_BAK_DIR):
            shutil.rmtree(SAFE_BAK_DIR)

        # 1. Przenosimy stary PLUGIN_DIR do UKRYTEGO backupu
        if os.path.exists(PLUGIN_DIR):
             shutil.move(PLUGIN_DIR, SAFE_BAK_DIR)
        
        # 2. Przenosimy nową zawartość (znalezioną ścieżkę SRC) do PLUGIN_DIR
        shutil.move(src, PLUGIN_DIR)

        # 3. Usuwamy backup, aby nie zajmował miejsca
        if os.path.exists(SAFE_BAK_DIR):
             shutil.rmtree(SAFE_BAK_DIR)


        # przywróć uprawnienia
        os.chmod(PLUGIN_DIR, 0o755)
        for root, dirs, files in os.walk(PLUGIN_DIR):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o644)
                if f.endswith(".py"):
                    os.chmod(os.path.join(root, f), 0o755)
                    
        # zapisz nową wersję
        with open(os.path.join(PLUGIN_DIR, "VERSION"), "w") as v:
            v.write(_get_remote_version())
        return True
        
    except Exception as e:
        # W przypadku błędu, próbujemy przywrócić ukryty backup
        if os.path.exists(SAFE_BAK_DIR) and not os.path.exists(PLUGIN_DIR):
             print("Przywracam backup...")
             shutil.move(SAFE_BAK_DIR, PLUGIN_DIR)
        raise e
        
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
