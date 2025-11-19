# -*- coding: utf-8 -*-
import os, requests, json, tempfile, shutil

REPO_ZIP   = "https://github.com/OliOli2013/IPTV-Dream-Plugin/archive/refs/heads/main.zip"
PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"

def _get_local_version():
    """wersja = data commitu zapisana w pliku VERSION"""
    try:
        with open(os.path.join(PLUGIN_DIR, "VERSION"), "r") as f:
            return f.read().strip()
    except Exception:
        return "unknown"

def _get_remote_version():
    """pobiera datę ostatniego commitu z API GitHub"""
    try:
        api = "https://api.github.com/repos/OliOli2013/IPTV-Dream-Plugin/commits?per_page=1"
        r = requests.get(api, timeout=10)
        r.raise_for_status()
        return r.json()[0]["commit"]["committer"]["date"][:10]   # YYYY-MM-DD
    except Exception:
        return None

def check_update():
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
    try:
        r = requests.get(REPO_ZIP, timeout=30)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            f.write(r.content)
        shutil.unpack_archive(zip_path, tmp)
        
        # Bierzemy główny folder rozpakowanego repozytorium
        main_folder_name = "IPTV-Dream-Plugin-main"
        src = os.path.join(tmp, main_folder_name)
        
        # Weryfikacja: Jeśli nie ma głównego folderu repo, coś jest źle
        if not os.path.isdir(src):
            raise Exception("bad archive structure: main folder missing")

        # Nowa, bardziej tolerancyjna logika przenoszenia:
        
        # 1. NAZWA KATALOGU BACKUPU: Używamy kropki, aby ukryć go przed skanerem Enigmy2
        bak = PLUGIN_DIR + ".bak"
        hidden_bak = PLUGIN_DIR + ".bak_hidden" # Używamy tymczasowej nazwy

        if os.path.exists(bak):
            shutil.rmtree(bak)

        # 2. Tworzymy nowy folder IPTVDream tymczasowo obok
        temp_dest = os.path.join(tmp, "IPTVDream_new")
        shutil.copytree(src, temp_dest)

        # 3. Przenosimy stary PLUGIN_DIR do UKRYTEGO backupu
        if os.path.exists(PLUGIN_DIR):
             shutil.move(PLUGIN_DIR, hidden_bak)
        
        # 4. Przenosimy nową zawartość do PLUGIN_DIR
        shutil.move(temp_dest, PLUGIN_DIR)

        # 5. Bezpieczne usunięcie starego backupu
        if os.path.exists(hidden_bak):
             shutil.rmtree(hidden_bak)


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
        if os.path.exists(hidden_bak) and not os.path.exists(PLUGIN_DIR):
             print("Przywracam backup...")
             shutil.move(hidden_bak, PLUGIN_DIR)
        raise e
        
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
