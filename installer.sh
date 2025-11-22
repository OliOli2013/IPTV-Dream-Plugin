#!/bin/sh
#
# Skrypt instalacyjny dla wtyczki IPTV Dream
# Wersja skryptu: 3.0 (Full Package)
#

# --- Konfiguracja ---
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"
BASE_URL="https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main"

# Lista plików w głównym katalogu wtyczki (Dodałem VERSION!)
FILES_ROOT="
__init__.py
dream.py
export.py
file_pick.py
icon.png
plugin.png
plugin.py
vkb_input.py
VERSION
" 

# Lista plików w podkatalogu /tools (Dodałem __init__.py!)
FILES_TOOLS="
__init__.py
bouquet_picker.py
epg_picon.py
lang.py
mac_portal.py
updater.py
xtream_one_window.py
" 

# --- Logika skryptu ---
echo "=================================================="
echo "    Instalator wtyczki IPTV Dream v3.2"
echo "=================================================="

if ! command -v wget >/dev/null 2>&1; then
    echo "BŁĄD: Brak programu wget."
    exit 1
fi

echo ">>> Czyszczenie starej wersji..."
rm -rf "$PLUGIN_PATH"
mkdir -p "$PLUGIN_PATH/tools"

# Funkcja pobierania
download_file() {
    url=$1
    dest=$2
    wget -q "--no-check-certificate" "$url" -O "$dest"
    if [ $? -ne 0 ]; then
        echo "BŁĄD pobierania: $url"
        # Nie przerywamy, próbujemy dalej, ale informujemy
    else
        echo "OK: $(basename $dest)"
    fi
}

echo ">>> Pobieranie plików głównych..."
for file in $FILES_ROOT; do
    download_file "$BASE_URL/$file" "$PLUGIN_PATH/$file"
done

echo ">>> Pobieranie narzędzi (tools)..."
for file in $FILES_TOOLS; do
    download_file "$BASE_URL/tools/$file" "$PLUGIN_PATH/tools/$file"
done

# Kopia bezpieczeństwa dla vkb_input (kompatybilność)
if [ -f "$PLUGIN_PATH/vkb_input.py" ]; then
    cp "$PLUGIN_PATH/vkb_input.py" "$PLUGIN_PATH/tools/vkb_input.py"
fi

# Ustawienie uprawnień (Kluczowe!)
chmod 755 "$PLUGIN_PATH"/*.py
chmod 755 "$PLUGIN_PATH"/tools/*.py
chmod 644 "$PLUGIN_PATH"/VERSION
chmod 644 "$PLUGIN_PATH"/*.png

echo "=================================================="
echo "✅ Instalacja zakończona!"
echo "   Wykonaj restart GUI, aby wtyczka się pojawiła."
echo "=================================================="

exit 0
