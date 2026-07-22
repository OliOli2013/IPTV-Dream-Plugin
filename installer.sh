#!/bin/sh
#
# IPTV Dream - installer (GitHub ZIP) + GUI restart
# Obsługuje repo "płaskie" (plugin.py w root) oraz zagnieżdżone (Plugins/Extensions/IPTVDream).
#

# ===== Repo (Twoje) =====
GITHUB_OWNER="${GITHUB_OWNER:-OliOli2013}"
GITHUB_REPO="${GITHUB_REPO:-IPTV-Dream-Plugin}"
GITHUB_REF="${GITHUB_REF:-main}"          # branch lub tag (np. main albo v6.0.4)

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

# ===== Wykrywanie struktury źródeł =====
NESTED_SRC="$ROOT_DIR/Plugins/Extensions/IPTVDream"
FLAT_SRC="$ROOT_DIR"

if [ -d "$NESTED_SRC" ]; then
  SRC_DIR="$NESTED_SRC"
  log "Wykryto strukturę zagnieżdżoną: Plugins/Extensions/IPTVDream"
elif [ -f "$FLAT_SRC/plugin.py" ] && [ -d "$FLAT_SRC/tools" ]; then
  SRC_DIR="$FLAT_SRC"
  log "Wykryto strukturę płaską (plugin.py w root repo)."
else
  # ostatnia próba: poszukaj katalogu IPTVDream w głębi
  FOUND="$(find "$ROOT_DIR" -type f -name "plugin.py" -path "*/IPTVDream/*" | head -n 1)"
  if [ -n "$FOUND" ]; then
    SRC_DIR="$(dirname "$FOUND")"
    log "Wykryto IPTVDream w głębi: $SRC_DIR"
  else
    die "Nie wykryto źródeł wtyczki (brak plugin.py/tools). Sprawdź strukturę repo."
  fi
fi

log "Backup poprzedniej wersji (jeśli istnieje)..."
if [ -d "$PLUGIN_DST" ]; then
  BACKUP="/tmp/IPTVDream_backup_$(date +%Y%m%d_%H%M%S)"
  cp -a "$PLUGIN_DST" "$BACKUP" || die "Nie mogę wykonać kopii: $BACKUP"
  echo "    OK: $BACKUP"
fi

log "Czysta instalacja (usuwanie starej wersji)..."
rm -rf "$PLUGIN_DST" || die "Nie mogę usunąć starego katalogu wtyczki."

log "Kopiowanie nowej wersji do: $PLUGIN_DST"
mkdir -p "$PLUGIN_DST" || die "Nie mogę utworzyć katalogu docelowego."

# Kopiuj zawartość źródła do katalogu wtyczki.
# W repo "płaskim" pominie to śmieci typu .github (jeśli byłyby w ZIP), ale GitHub ZIP i tak ich nie daje zwykle.
cp -a "$SRC_DIR"/* "$PLUGIN_DST"/ || die "Błąd kopiowania plików wtyczki."

# Walidacja: plugin.py musi istnieć
[ -f "$PLUGIN_DST/plugin.py" ] || die "Po instalacji brakuje $PLUGIN_DST/plugin.py (błędne źródła lub struktura)."

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
