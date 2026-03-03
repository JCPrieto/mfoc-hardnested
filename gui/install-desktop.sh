#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${SCRIPT_DIR}"
RES_DIR="${APP_DIR}/resources"

DESKTOP_ID="io.github.mfoc.hardnested.gui.desktop"
ICON_NAME="io.github.mfoc.hardnested.gui.svg"

APP_DST_DIR="${HOME}/.local/share/applications"
ICON_DST_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
ICON_DST_PATH="${ICON_DST_DIR}/${ICON_NAME}"

mkdir -p "${APP_DST_DIR}" "${ICON_DST_DIR}"

sed -e "s|@APP_DIR@|${APP_DIR}|g" \
    -e "s|@ICON_PATH@|${ICON_DST_PATH}|g" \
    "${RES_DIR}/${DESKTOP_ID}.in" > "${APP_DST_DIR}/${DESKTOP_ID}"
chmod 0644 "${APP_DST_DIR}/${DESKTOP_ID}"
cp "${RES_DIR}/${ICON_NAME}" "${ICON_DST_PATH}"
chmod 0644 "${ICON_DST_PATH}"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${APP_DST_DIR}" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q "${HOME}/.local/share/icons/hicolor" || true
fi

echo "Installed desktop launcher:"
echo "  ${APP_DST_DIR}/${DESKTOP_ID}"
echo "Installed icon:"
echo "  ${ICON_DST_PATH}"
