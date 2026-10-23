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
  if [ -n "$BACKUP" ] && [ -d "$BACKUP" ]; then
    echo ">>> Przywracanie poprzedniej wersji..."
    rm -rf "$PLUGIN_DST" 2>/dev/null
    cp -a "$BACKUP" "$PLUGIN_DST" 2>/dev/null || true
  fi
  rm -rf "$TMP_BASE" 2>/dev/null
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Brak programu: $1"
}

validate_python_tree() {
  # Bez compileall/py_compile: dostepne takze w okrojonych obrazach Enigma2.
  python3 - "$1" <<'PYVALIDATE'
import os
import sys

root = sys.argv[1]
if not os.path.isdir(root):
    sys.stderr.write('BŁĄD: Brak katalogu do walidacji: %s\n' % root)
    sys.exit(1)

errors = 0
checked = 0

def walk_error(exc):
    global errors
    errors += 1
    sys.stderr.write('BŁĄD odczytu katalogu: %s\n' % exc)

for directory, subdirs, files in os.walk(root, onerror=walk_error):
    subdirs[:] = [name for name in subdirs if name not in
                  ('.git', '.github', '__pycache__', 'tests', 'docs', 'packaging')]
    for name in files:
        if not name.endswith('.py'):
            continue
        path = os.path.join(directory, name)
        try:
            with open(path, 'rb') as handle:
                compile(handle.read(), path, 'exec')
            checked += 1
        except Exception as exc:
            errors += 1
            sys.stderr.write('BŁĄD Python %s: %s\n' % (path, exc))

if errors:
    sys.stderr.write('BŁĄD: Nieudana walidacja (%s problemów).\n' % errors)
    sys.exit(1)
if not checked:
    sys.stderr.write('BŁĄD: Nie znaleziono plików Python do sprawdzenia.\n')
    sys.exit(1)
print('>>> Walidacja składni Python OK: %s plików (bez py_compile).' % checked)
PYVALIDATE
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
need_cmd python3
if [ "$RESTART_GUI" -eq 1 ]; then
  need_cmd init
fi

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

# Validate downloaded source before touching the installed version.
for REQUIRED in plugin.py dream_v6.py export_v2.py core/playlist_loader.py tools/net.py tools/lang.py; do
  [ -f "$SRC_DIR/$REQUIRED" ] || die "Niepełne źródła aktualizacji: brak $REQUIRED."
done
validate_python_tree "$SRC_DIR" || die "Walidacja pobranych źródeł nie powiodła się. Stara wersja nie została zmieniona."
find "$SRC_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} \; 2>/dev/null

BACKUP=""
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

# Usuń artefakty repozytorium i historyczne duplikaty, których runtime nie używa.
rm -f \
  "$PLUGIN_DST/dream.py" "$PLUGIN_DST/dream_v2.py" "$PLUGIN_DST/export.py" \
  "$PLUGIN_DST/test_plugin.py" "$PLUGIN_DST"/*.ipk "$PLUGIN_DST"/*.deb 2>/dev/null
rm -f \
  "$PLUGIN_DST/tools/epg_picon_fixed.py" "$PLUGIN_DST/tools/mac_portal_v6.py" \
  "$PLUGIN_DST/tools/picon_manager.py" "$PLUGIN_DST/tools/xtream_one_window.py" \
  "$PLUGIN_DST/tools/vkb_input.py" "$PLUGIN_DST/pic/iptvdream_mark.png" 2>/dev/null

# Pliki potrzebne tylko na GitHubie / w release nie powinny trafiać do runtime tunera.
rm -f \
  "$PLUGIN_DST/GITHUB_REPLACE_INSTRUCTIONS.txt" "$PLUGIN_DST/FILES_TO_DELETE_GITHUB.txt" \
  "$PLUGIN_DST"/CHANGED_FILES_*.txt "$PLUGIN_DST/RELEASE_TITLE.txt" \
  "$PLUGIN_DST/RELEASE_BODY_PL.md" "$PLUGIN_DST/RELEASE_BODY_EN.md" \
  "$PLUGIN_DST/SHA256SUMS.txt" "$PLUGIN_DST/build_ipk.sh" \
  "$PLUGIN_DST"/AUDIT_*.md "$PLUGIN_DST"/GITHUB_UPLOAD_*.txt \
  "$PLUGIN_DST"/*.patch 2>/dev/null
rm -rf "$PLUGIN_DST/.github" "$PLUGIN_DST/screenshots" "$PLUGIN_DST/release" "$PLUGIN_DST/docs" \
  "$PLUGIN_DST/tests" "$PLUGIN_DST/packaging" 2>/dev/null

# Walidacja: wymagane pliki + składnia Pythona przed restartem GUI.
[ -f "$PLUGIN_DST/plugin.py" ] || die "Po instalacji brakuje $PLUGIN_DST/plugin.py (błędne źródła lub struktura)."
[ -f "$PLUGIN_DST/dream_v6.py" ] || die "Po instalacji brakuje dream_v6.py."
[ -f "$PLUGIN_DST/core/playlist_loader.py" ] || die "Po instalacji brakuje core/playlist_loader.py."
validate_python_tree "$PLUGIN_DST" || die "Walidacja składni Python po instalacji nie powiodła się."

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
if [ -n "$BACKUP" ] && [ -d "$BACKUP" ]; then
  rm -rf "$BACKUP" 2>/dev/null
fi
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
