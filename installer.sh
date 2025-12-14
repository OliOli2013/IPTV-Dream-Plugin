#!/bin/sh
#
# IPTV Dream - installer (GitHub ZIP) + GUI restart
# Repo: https://github.com/OliOli2013/IPTV-Dream-Plugin (branch domyślnie: main)
#

# ===== Repo (Twoje) =====
GITHUB_OWNER="${GITHUB_OWNER:-OliOli2013}"
GITHUB_REPO="${GITHUB_REPO:-IPTV-Dream-Plugin}"
GITHUB_REF="${GITHUB_REF:-main}"          # branch lub tag (np. main albo v6.0.4)

# W ZIP-ie wtyczka ma być w tej ścieżce (dopasuj, jeśli zmienisz strukturę repo)
SRC_SUBDIR="Plugins/Extensions/IPTVDream"

# Docelowy katalog wtyczki w Enigma2
PLUGIN_DST="/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"

# Katalog tymczasowy
TMP_BASE="/tmp/iptvdream_install.$$"

# Restart GUI domyślnie TAK; wyłącz opcją --no-restart
RESTART_GUI=1

usage() {
  cat <<EOF
IPTV Dream installer

Użycie:
  ./installer.sh [--ref <branch|tag>] [--no-restart]

Opcje:
  --ref <x>        Instaluj z branch/tag (np. main, master, v6.0.4)
  --no-restart     Nie restartuj GUI po instalacji

Zmienne środowiskowe (opcjonalnie):
  GITHUB_OWNER, GITHUB_REPO, GITHUB_REF
EOF
  exit 0
}

log() { echo ">>> $*"; }

die() {
  echo "BŁĄD: $*"
  rm -rf "$TMP_BASE" 2>/dev/null
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Brak programu: $1"
}

# ===== Parsowanie argumentów =====
while [ $# -gt 0 ]; do
  case "$1" in
    --ref)
      shift
      [ -n "$1" ] || die "Brak wartości po --ref"
      GITHUB_REF="$1"
      ;;
    --no-restart)
      RESTART_GUI=0
      ;;
    -h|--help)
      usage
      ;;
    *)
      die "Nieznana opcja: $1 (użyj --help)"
      ;;
  esac
  shift
done

echo "=================================================="
echo " IPTV Dream Installer - GitHub ZIP"
echo " Repo: ${GITHUB_OWNER}/${GITHUB_REPO}  Ref: ${GITHUB_REF}"
echo " Dest: ${PLUGIN_DST}"
echo " Restart GUI: $( [ "$RESTART_GUI" -eq 1 ] && echo TAK || echo NIE )"
echo "=================================================="

# ===== Wymagane narzędzia =====
need_cmd wget
need_cmd unzip
need_cmd cp
need_cmd rm
need_cmd mkdir
need_cmd find
need_cmd head
need_cmd date
need_cmd sync
need_cmd sleep
need_cmd init

mkdir -p "$TMP_BASE" || die "Nie mogę utworzyć katalogu tymczasowego: $TMP_BASE"

# ZIP URL (branch lub tag)
ZIP_URL_HEADS="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/archive/refs/heads/${GITHUB_REF}.zip"
ZIP_URL_TAGS="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/archive/refs/tags/${GITHUB_REF}.zip"
ZIP_FILE="$TMP_BASE/src.zip"

log "Pobieranie paczki (branch/tag)..."
wget -q -O "$ZIP_FILE" "$ZIP_URL_HEADS"
if [ $? -ne 0 ] || [ ! -s "$ZIP_FILE" ]; then
  wget -q -O "$ZIP_FILE" "$ZIP_URL_TAGS" || die "Nie mogę pobrać ZIP z GitHuba (branch/tag)."
fi

log "Rozpakowywanie..."
unzip -q "$ZIP_FILE" -d "$TMP_BASE/unzip" || die "Błąd rozpakowania ZIP."

# katalog główny rozpakowanego repo: IPTV-Dream-Plugin-main lub IPTV-Dream-Plugin-vX
ROOT_DIR="$(find "$TMP_BASE/unzip" -maxdepth 1 -type d -name "${GITHUB_REPO}-*" | head -n 1)"
[ -n "$ROOT_DIR" ] || die "Nie znaleziono katalogu repo po rozpakowaniu."

SRC_DIR="$ROOT_DIR/$SRC_SUBDIR"
[ -d "$SRC_DIR" ] || die "Nie znaleziono w ZIP ścieżki: $SRC_SUBDIR (sprawdź strukturę repo)."

log "Backup poprzedniej wersji (jeśli istnieje)..."
if [ -d "$PLUGIN_DST" ]; then
  BACKUP="/tmp/IPTVDream_backup_$(date +%Y%m%d_%H%M%S)"
  cp -a "$PLUGIN_DST" "$BACKUP" || die "Nie mogę wykonać kopii: $BACKUP"
  echo "    OK: $BACKUP"
fi

log "Czysta instalacja (usuwanie starej wersji)..."
rm -rf "$PLUGIN_DST" || die "Nie mogę usunąć starego katalogu wtyczki."

log "Kopiowanie nowej wersji..."
mkdir -p "$(dirname "$PLUGIN_DST")" || die "Nie mogę utworzyć katalogu docelowego."
cp -a "$SRC_DIR" "$PLUGIN_DST" || die "Błąd kopiowania plików wtyczki."

log "Czyszczenie cache Pythona..."
rm -rf \
  "$PLUGIN_DST/__pycache__" \
  "$PLUGIN_DST/core/__pycache__" \
  "$PLUGIN_DST/tools/__pycache__" 2>/dev/null

log "Ustawianie uprawnień..."
find "$PLUGIN_DST" -type f -name "*.py" -exec chmod 755 {} \; 2>/dev/null
find "$PLUGIN_DST" -type f -name "*.sh" -exec chmod 755 {} \; 2>/dev/null
find "$PLUGIN_DST" -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) -exec chmod 644 {} \; 2>/dev/null
find "$PLUGIN_DST" -type f \( -name "*.txt" -o -name "*.md" -o -name "VERSION" \) -exec chmod 644 {} \; 2>/dev/null

log "Sprzątanie plików tymczasowych..."
rm -rf "$TMP_BASE" 2>/dev/null
sync

echo "=================================================="
echo " OK: Instalacja zakończona."
echo "=================================================="

if [ "$RESTART_GUI" -eq 1 ]; then
  echo ">>> Restart GUI..."
  init 4 >/dev/null 2>&1
  sleep 2
  init 3 >/dev/null 2>&1
fi

exit 0
