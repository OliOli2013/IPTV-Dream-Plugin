#!/bin/sh
# Skrypt instalacyjny dla wtyczki IPTV Dream

# Ustawienie ścieżki do folderu z wtyczkami Enigma2
PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"

echo ">>> Usuwanie poprzedniej wersji wtyczki (jeśli istnieje)..."
rm -rf ${PLUGIN_PATH}

echo ">>> Tworzenie folderu dla nowej wersji wtyczki..."
mkdir -p ${PLUGIN_PATH}

echo ">>> Pobieranie plików wtyczki z GitHub..."
wget -q "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/dream.py" -P ${PLUGIN_PATH}
wget -q "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/export.py" -P ${PLUGIN_PATH}
wget -q "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/file_pick.py" -P ${PLUGIN_PATH}
wget -q "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/icon.png" -P ${PLUGIN_PATH}
wget -q "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/__init__.py" -P ${PLUGIN_PATH}
wget -q "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/plugin.png" -P ${PLUGIN_PATH}
wget -q "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/plugin.py" -P ${PLUGIN_PATH}
wget -q "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/vkb_input.py" -P ${PLUGIN_PATH}

echo ">>> Ustawianie odpowiednich uprawnień dla plików..."
chmod -R 755 ${PLUGIN_PATH}

echo "*****************************************************"
echo "** **"
echo "** Instalacja zakończona pomyślnie!           **"
echo "** Proszę zrestartować Enigma2, aby zmiany      **"
echo "** zostały wprowadzone.                 **"
echo "** **"
echo "*****************************************************"

exit 0
