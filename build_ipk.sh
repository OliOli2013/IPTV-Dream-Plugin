#!/bin/sh
set -eu
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec python3 "$ROOT_DIR/build_packages.py" "${1:-$ROOT_DIR/release}"
