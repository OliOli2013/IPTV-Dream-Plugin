#!/bin/sh
#
# Skrypt instalacyjny dla wtyczki IPTV Dream
# Pobiera najnowsze pliki wtyczki bezpośrednio z repozytorium GitHub.
#
# Wersja skryptu: 3.0 (Clean Install)
#

# --- Konfiguracja ---
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"
BASE_URL="https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main"

# Lista plików w głównym katalogu wtyczki
FILES_ROOT="
__init__.py
dream.py
export.py
file_pick.py
icon.png
plugin.png
plugin.py
vkb_input.py
" 

# Lista plików w podkatalogu /tools
# UWAGA: vkb_input.py usunięte z tej listy, bo jest już w root
FILES_TOOLS="
bouquet_picker.py
epg_picon.py
lang.py
mac_portal.py
updater.py
xtream_one_window.py
" 

# --- Logika skryptu ---
echo "=================================================="
echo "    Instalator wtyczki IPTV Dream by Paweł Pawłek"
echo "=================================================="

# Sprawdzenie, czy jest dostępne wget
if ! command -v wget >/dev/null 2>&1; then
    echo "BŁĄD: Do instalacji wymagany jest program wget."
    exit 1
fi

echo ">>> Usuwanie poprzedniej wersji wtyczki..."
rm -rf "$PLUGIN_PATH"

echo ">>> Tworzenie struktury katalogów..."
mkdir -p "$PLUGIN_PATH/tools"

# Funkcja do pobierania plików
download_file() {
    url=$1
    dest=$2
    wget -q "--no-check-certificate" "$url" -O "$dest"
    if [ $? -ne 0 ]; then
        echo "BŁĄD: Nie udało się pobrać pliku $url"
        exit 1
    fi
}

echo ">>> Pobieranie plików głównych..."
for file in $FILES_ROOT; do
    echo "   - Pobieranie $file..."
    download_file "$BASE_URL/$file" "$PLUGIN_PATH/$file"
done

echo ">>> Pobieranie plików z katalogu /tools..."
for file in $FILES_TOOLS; do
    echo "   - Pobieranie $file..."
    download_file "$BASE_URL/tools/$file" "$PLUGIN_PATH/tools/$file"
done

# --- FIX DLA PYTHON PACKAGE ---
# Tworzymy __init__.py w tools, jeśli go nie ma (naprawia importy)
echo ">>> Tworzenie brakującego __init__.py w tools..."
touch "$PLUGIN_PATH/tools/__init__.py"

# === USTAWIENIE UPRAWNIEŃ ===
echo ">>> Ustawianie uprawnień wykonywania (chmod 755)..."
chmod 755 "$PLUGIN_PATH"/*.py
chmod 755 "$PLUGIN_PATH"/tools/*.py

echo "=================================================="
echo "✅ Instalacja zakończona pomyślnie!"
echo "   Aby zmiany były widoczne, zrestartuj GUI."
echo "=================================================="

exit 0
