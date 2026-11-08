#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
    printf 'Budowa wymaga macOS na Apple Silicon.\n' >&2
    exit 1
fi
if [[ -z "${PYTHON_BIN:-}" ]]; then
    python3.12 -m venv .venv
    PYTHON_BIN=.venv/bin/python
fi
"$PYTHON_BIN" -m pip install -r requirements-macos-lock.txt
"$PYTHON_BIN" -m PyInstaller --clean --noconfirm --windowed \
    --target-architecture arm64 --name "Polecenie przelewu" \
    --osx-bundle-identifier pl.drukipocztowe.desktop \
    --icon "assets/icon.icns" \
    --add-data "assets/template.pdf:assets" \
    --add-data "assets/icon.icns:assets" main.py
printf '\nZbudowano dist/Polecenie przelewu.app\n'
