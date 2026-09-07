#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
VERSION="$(tr -d ' \t\r\n' < "$ROOT_DIR/VERSION")"
OUTPUT_DIR="${1:-$ROOT_DIR/release}"
PACKAGE="enigma2-plugin-extensions-iptvdream"
IPK_PATH="$OUTPUT_DIR/${PACKAGE}_${VERSION}_all.ipk"
PLUGIN_REL="usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"
BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/iptvdream-build.XXXXXX")"

cleanup() {
    rm -rf "$BUILD_DIR"
}
trap cleanup EXIT HUP INT TERM

case "$VERSION" in
    ''|*[!0-9A-Za-z._+-]*)
        echo "Invalid VERSION: $VERSION" >&2
        exit 1
        ;;
esac

for command_name in ar tar gzip sed find; do
    command -v "$command_name" >/dev/null 2>&1 || {
        echo "Missing build command: $command_name" >&2
        exit 1
    }
done

mkdir -p "$OUTPUT_DIR" "$BUILD_DIR/control" "$BUILD_DIR/data/$PLUGIN_REL"

ROOT_FILES="CHANGELOG.txt LICENSE README.md VERSION __init__.py dream_v6.py export_v2.py file_pick.py icon.png installer.sh plugin.png plugin.py setup.xml vkb_input.py"
for relative in $ROOT_FILES; do
    test -f "$ROOT_DIR/$relative" || {
        echo "Missing runtime file: $relative" >&2
        exit 1
    }
    cp -a "$ROOT_DIR/$relative" "$BUILD_DIR/data/$PLUGIN_REL/"
done

for relative in core tools pic; do
    test -d "$ROOT_DIR/$relative" || {
        echo "Missing runtime directory: $relative" >&2
        exit 1
    }
    cp -a "$ROOT_DIR/$relative" "$BUILD_DIR/data/$PLUGIN_REL/"
done

find "$BUILD_DIR/data" -type d -name __pycache__ -prune -exec rm -rf {} \;
find "$BUILD_DIR/data" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
find "$BUILD_DIR/data" -type d -exec chmod 755 {} \;
find "$BUILD_DIR/data" -type d -exec chmod g-s {} \;
find "$BUILD_DIR/data" -type f -exec chmod 644 {} \;
find "$BUILD_DIR/data" -type f \( -name '*.py' -o -name '*.sh' \) -exec chmod 755 {} \;

sed "s/@VERSION@/$VERSION/g" "$ROOT_DIR/packaging/control.in" > "$BUILD_DIR/control/control"
cp "$ROOT_DIR/packaging/postinst" "$BUILD_DIR/control/postinst"
chmod 644 "$BUILD_DIR/control/control"
chmod 755 "$BUILD_DIR/control/postinst"
printf '2.0\n' > "$BUILD_DIR/debian-binary"

SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(date -u +%s)}"
TAR_OPTIONS="--sort=name --format=gnu --mtime=@$SOURCE_DATE_EPOCH --owner=0 --group=0 --numeric-owner"
(
    cd "$BUILD_DIR/control"
    # shellcheck disable=SC2086
    tar $TAR_OPTIONS -cf - . | gzip -n -9 > "$BUILD_DIR/control.tar.gz"
)
(
    cd "$BUILD_DIR/data"
    # shellcheck disable=SC2086
    tar $TAR_OPTIONS -cf - . | gzip -n -9 > "$BUILD_DIR/data.tar.gz"
)

rm -f "$IPK_PATH"
(
    cd "$BUILD_DIR"
    ar rcsD "$IPK_PATH" debian-binary control.tar.gz data.tar.gz
)

echo "$IPK_PATH"
