#!/bin/sh
#
# Skrypt instalacyjny dla wtyczki IPTV Dream
# Wersja skryptu: 4.1 (Update dla v4.1)
#

# --- Konfiguracja ---
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"
BASE_URL="https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main"

# Pliki w katalogu głównym wtyczki
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

# Pliki w podkatalogu /tools (Doszedł webif.py!)
FILES_TOOLS="
__init__.py
bouquet_picker.py
epg_picon.py
lang.py
mac_portal.py
updater.py
webif.py
xtream_one_window.py
" 

# Pliki w podkatalogu /pic (Nowy katalog!)
FILES_PIC="
qrcode.png
"

# --- Logika skryptu ---
echo "=================================================="
echo "    Instalator wtyczki IPTV Dream v4.0"
echo "=================================================="

if ! command -v wget >/dev/null 2>&1; then
    echo "BŁĄD: Brak programu wget."
    exit 1
fi

echo ">>> Przygotowanie środowiska..."
# Nie usuwamy całego katalogu od razu, żeby zachować pliki konfiguracyjne użytkownika (jeśli są)
mkdir -p "$PLUGIN_PATH/tools"
mkdir -p "$PLUGIN_PATH/pic"

# Funkcja pobierania
download_file() {
    url=$1
    dest=$2
    wget -q "--no-check-certificate" "$url" -O "$dest"
    if [ $? -ne 0 ]; then
        echo "BŁĄD pobierania: $url"
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

echo ">>> Pobieranie grafik (pic)..."
for file in $FILES_PIC; do
    download_file "$BASE_URL/pic/$file" "$PLUGIN_PATH/pic/$file"
done

# Kopia bezpieczeństwa dla vkb_input (kompatybilność wsteczna)
if [ -f "$PLUGIN_PATH/vkb_input.py" ]; then
    cp "$PLUGIN_PATH/vkb_input.py" "$PLUGIN_PATH/tools/vkb_input.py"
fi

# Ustawienie uprawnień
echo ">>> Nadawanie uprawnień..."
chmod 755 "$PLUGIN_PATH"/*.py
chmod 755 "$PLUGIN_PATH"/tools/*.py
chmod 644 "$PLUGIN_PATH"/VERSION
chmod 644 "$PLUGIN_PATH"/*.png
chmod 644 "$PLUGIN_PATH"/pic/*.png

echo "=================================================="
echo "✅ Instalacja zakończona sukcesem!"
echo "   Wykonaj restart GUI (Menu -> Czuwanie -> Restart GUI)"
echo "=================================================="

exit 0
