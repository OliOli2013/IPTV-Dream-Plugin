#!/bin/sh
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"
BASE_URL="https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main"

FILES_ROOT="__init__.py dream.py export.py file_pick.py icon.png plugin.png plugin.py vkb_input.py"
FILES_TOOLS="bouquet_picker.py epg_picon.py lang.py mac_portal.py updater.py xtream_one_window.py"

if ! command -v wget >/dev/null 2>&1; then echo "Brak wget"; exit 1; fi
rm -rf "$PLUGIN_PATH"; mkdir -p "$PLUGIN_PATH/tools"

download_file() {
    wget -q "--no-check-certificate" "$1" -O "$2"
}

echo "Pobieranie..."
for f in $FILES_ROOT; do download_file "$BASE_URL/$f" "$PLUGIN_PATH/$f"; done
for f in $FILES_TOOLS; do download_file "$BASE_URL/tools/$f" "$PLUGIN_PATH/tools/$f"; done

if [ -f "$PLUGIN_PATH/vkb_input.py" ]; then cp "$PLUGIN_PATH/vkb_input.py" "$PLUGIN_PATH/tools/vkb_input.py"; fi

chmod 755 "$PLUGIN_PATH"/*.py
chmod 755 "$PLUGIN_PATH"/tools/*.py
echo "Zainstalowano! Zrestartuj GUI."
exit 0
