#!/bin/sh
#
# Skrypt instalacyjny dla wtyczki IPTV Dream
# Automatycznie pobiera i instaluje najnowszą wersję z GitHub.
#
# Wersja skryptu: 1.2
#

# --- Konfiguracja ---
REPO="OliOli2013/IPTV-Dream-Plugin"
TMP_DIR="/tmp"

# --- Logika skryptu ---
echo "=================================================="
echo "    Instalator wtyczki IPTV Dream by Paweł Pawłek"
echo "=================================================="

# Sprawdzenie, czy jest dostępne curl lub wget
if command -v curl >/dev/null 2>&1; then
    DOWNLOADER="curl"
elif command -v wget >/dev/null 2>&1; then
    DOWNLOADER="wget"
else
    echo "BŁĄD: Nie znaleziono ani curl, ani wget. Instalacja niemożliwa."
    exit 1
fi

echo ">>> Wyszukiwanie najnowszej wersji wtyczki..."

# Użycie API GitHub do znalezienia URL najnowszego pliku .ipk
PKG_URL=$(
    if [ "$DOWNLOADER" = "curl" ]; then
        curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep 'browser_download_url' | grep '\.ipk"' | cut -d'"' -f4
    else
        wget -q -O - "https://api.github.com/repos/$REPO/releases/latest" | grep 'browser_download_url' | grep '\.ipk"' | cut -d'"' -f4
    fi
)

# Sprawdzenie, czy udało się znaleźć plik
if [ -z "$PKG_URL" ]; then
    echo "BŁĄD: Nie udało się znaleźć pliku .ipk w najnowszym wydaniu na GitHubie."
    exit 1
fi

FILENAME=$(basename "$PKG_URL")
DEST_FILE="$TMP_DIR/$FILENAME"

echo ">>> Znaleziono plik: $FILENAME"
echo ">>> Pobieranie do katalogu $TMP_DIR..."

# Pobieranie pliku
if [ "$DOWNLOADER" = "curl" ]; then
    curl -LfsS "$PKG_URL" -o "$DEST_FILE"
else
    wget -q "$PKG_URL" -O "$DEST_FILE"
fi

# Sprawdzenie, czy pobieranie się udało
if [ $? -ne 0 ]; then
    echo "BŁĄD: Pobieranie pliku nie powiodło się."
    rm -f "$DEST_FILE"
    exit 1
fi

echo ">>> Instalowanie wtyczki za pomocą opkg..."
opkg install "$DEST_FILE"

echo ">>> Sprzątanie plików tymczasowych..."
rm -f "$DEST_FILE"

echo "=================================================="
echo "✅ Instalacja zakończona pomyślnie!"
echo "   Aby zmiany były widoczne, zrestartuj GUI."
echo "=================================================="

exit 0
