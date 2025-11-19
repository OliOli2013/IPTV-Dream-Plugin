# -*- coding: utf-8 -*-
import os, requests, json, tempfile, shutil

# URL do pobrania repozytorium jako ZIP
REPO_ZIP   = "https://github.com/OliOli2013/IPTV-Dream-Plugin/archive/refs/heads/main.zip"
PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"

def _get_local_version():
    """Pobiera wersję lokalną z pliku VERSION"""
    try:
        with open(os.path.join(PLUGIN_DIR, "VERSION"), "r") as f:
            return f.read().strip()
    except Exception:
        return "unknown"

def _get_remote_version():
    """Pobiera datę ostatniego commitu z API GitHub jako wersję"""
    try:
        api = "https://api.github.com/repos/OliOli2013/IPTV-Dream-Plugin/commits?per_page=1"
        # User-Agent jest wymagany przez GitHub API
        headers = {'User-Agent': 'Enigma2-IPTVDream-Updater'}
        r = requests.get(api, timeout=10, headers=headers)
        r.raise_for_status()
        return r.json()[0]["commit"]["committer"]["date"][:10]   # Format YYYY-MM-DD
    except Exception:
        return None

def check_update():
    """Zwraca krotkę (bool_czy_jest_update, wersja_lokalna, wersja_zdalna)"""
    local  = _get_local_version()
    remote = _get_remote_version()
    
    if not remote:
        return False, local, "Błąd sieci"
    
    # Jeśli wersje są różne, uznajemy to za aktualizację
    if remote != local:
        return True, local, remote
        
    return False, local, remote

def do_update():
    """Pobiera, rozpakowuje i podmienia pliki wtyczki"""
    tmp = tempfile.mkdtemp()
    zip_path = os.path.join(tmp, "update.zip")
    
    # Katalog na bezpieczny backup (ukryty)
    SAFE_BAK_DIR = os.path.join(os.path.dirname(PLUGIN_DIR), ".IPTVDream_BAK")
    
    try:
        # 1. Pobieranie
        headers = {'User-Agent': 'Enigma2-IPTVDream-Updater'}
        r = requests.get(REPO_ZIP, timeout=60, headers=headers)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            f.write(r.content)
            
        # 2. Rozpakowanie
        shutil.unpack_archive(zip_path, tmp)
        
        # 3. Inteligentne szukanie folderu źródłowego
        # GitHub zazwyczaj rozpakowuje do "NazwaRepo-main"
        extracted_root = os.path.join(tmp, "IPTV-Dream-Plugin-main")
        src = None

        # Sprawdzamy czy pliki są bezpośrednio w folderze -main (struktura płaska)
        if os.path.exists(os.path.join(extracted_root, "plugin.py")):
            src = extracted_root
        # Sprawdzamy czy są w podkatalogu IPTVDream (struktura zagnieżdżona)
        elif os.path.exists(os.path.join(extracted_root, "IPTVDream", "plugin.py")):
            src = os.path.join(extracted_root, "IPTVDream")
        # Fallback: szukamy gdziekolwiek pliku plugin.py
        else:
            for root, dirs, files in os.walk(tmp):
                if "plugin.py" in files and "dream.py" in files:
                    src = root
                    break
        
        if not src:
            raise Exception("bad archive structure (plugin.py not found)")

        # 4. Backup starej wersji
        if os.path.exists(SAFE_BAK_DIR):
            shutil.rmtree(SAFE_BAK_DIR)
            
        if os.path.exists(PLUGIN_DIR):
             shutil.move(PLUGIN_DIR, SAFE_BAK_DIR)
        
        # 5. Przeniesienie nowej wersji na miejsce
        shutil.move(src, PLUGIN_DIR)

        # 6. Sprzątanie backupu po sukcesie
        if os.path.exists(SAFE_BAK_DIR):
             shutil.rmtree(SAFE_BAK_DIR)

        # 7. Nadanie uprawnień (ważne na Linuxie/E2)
        os.chmod(PLUGIN_DIR, 0o755)
        for root, dirs, files in os.walk(PLUGIN_DIR):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                fpath = os.path.join(root, f)
                if f.endswith(".sh") or f.endswith(".py"):
                    os.chmod(fpath, 0o755)
                else:
                    os.chmod(fpath, 0o644)
                    
        # Zapisanie nowej wersji
        with open(os.path.join(PLUGIN_DIR, "VERSION"), "w") as v:
            v.write(_get_remote_version())
            
        return True
        
    except Exception as e:
        # Rollback - przywracanie backupu w razie błędu
        print(f"[IPTVDream Updater] Błąd: {e}")
        if os.path.exists(SAFE_BAK_DIR) and not os.path.exists(PLUGIN_DIR):
             print("Przywracam poprzednią wersję...")
             shutil.move(SAFE_BAK_DIR, PLUGIN_DIR)
        raise e
        
    finally:
        # Sprzątanie plików tymczasowych
        if os.path.exists(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
