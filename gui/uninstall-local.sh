#!/usr/bin/env bash
set -euo pipefail

DESKTOP_FILE="${HOME}/.local/share/applications/io.github.mfoc.hardnested.gui.desktop"
ICON_FILE="${HOME}/.local/share/icons/hicolor/scalable/apps/io.github.mfoc.hardnested.gui.svg"

rm -f "${DESKTOP_FILE}" "${ICON_FILE}"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${HOME}/.local/share/applications" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Removed local desktop integration (if present)."
