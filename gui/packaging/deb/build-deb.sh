#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUI_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_DIR="$(cd "${GUI_DIR}/.." && pwd)"

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "dpkg-deb is required to build a .deb package." >&2
  exit 1
fi

VERSION="${1:-}"
if [[ -z "${VERSION}" ]]; then
  if [[ -f "${GUI_DIR}/VERSION" ]]; then
    VERSION="$(tr -d '[:space:]' < "${GUI_DIR}/VERSION")"
  fi
fi
if [[ -z "${VERSION}" ]]; then
  VERSION="$(sed -n "s/^AC_INIT(\\[mfoc-hardnested\\],\\[\\([^]]*\\)\\].*/\\1/p" "${REPO_DIR}/configure.ac" | head -n1)"
  VERSION="${VERSION:-0.0.0}"
fi

PKG_NAME="mfoc-hardnested-gui"
ARCH="all"
STAGE_DIR="$(mktemp -d "/tmp/${PKG_NAME}_${VERSION}_XXXXXX")"
PKG_ROOT="${STAGE_DIR}/${PKG_NAME}_${VERSION}_${ARCH}"

cleanup() {
  rm -rf "${STAGE_DIR}"
}
trap cleanup EXIT

mkdir -p "${PKG_ROOT}/DEBIAN"
mkdir -p "${PKG_ROOT}/opt/${PKG_NAME}"
mkdir -p "${PKG_ROOT}/usr/bin"
mkdir -p "${PKG_ROOT}/usr/share/applications"
mkdir -p "${PKG_ROOT}/usr/share/icons/hicolor/scalable/apps"

sed "s|@VERSION@|${VERSION}|g" "${SCRIPT_DIR}/control.in" > "${PKG_ROOT}/DEBIAN/control"
cp "${SCRIPT_DIR}/postinst" "${PKG_ROOT}/DEBIAN/postinst"
cp "${SCRIPT_DIR}/postrm" "${PKG_ROOT}/DEBIAN/postrm"
chmod 0755 "${PKG_ROOT}/DEBIAN/postinst" "${PKG_ROOT}/DEBIAN/postrm"

cp -r "${GUI_DIR}/controller" "${PKG_ROOT}/opt/${PKG_NAME}/"
cp -r "${GUI_DIR}/models" "${PKG_ROOT}/opt/${PKG_NAME}/"
cp -r "${GUI_DIR}/runner" "${PKG_ROOT}/opt/${PKG_NAME}/"
cp -r "${GUI_DIR}/ui" "${PKG_ROOT}/opt/${PKG_NAME}/"
cp "${GUI_DIR}/main.py" "${PKG_ROOT}/opt/${PKG_NAME}/main.py"

find "${PKG_ROOT}/opt/${PKG_NAME}" -type d -name "__pycache__" -prune -exec rm -rf {} +
rm -rf "${PKG_ROOT}/opt/${PKG_NAME}/runtime"

cp "${SCRIPT_DIR}/mfoc-hardnested-gui" "${PKG_ROOT}/usr/bin/mfoc-hardnested-gui"
chmod 0755 "${PKG_ROOT}/usr/bin/mfoc-hardnested-gui"

cp "${SCRIPT_DIR}/mfoc-hardnested-gui.desktop" "${PKG_ROOT}/usr/share/applications/mfoc-hardnested-gui.desktop"
cp "${GUI_DIR}/resources/io.github.mfoc.hardnested.gui.svg" \
  "${PKG_ROOT}/usr/share/icons/hicolor/scalable/apps/io.github.mfoc.hardnested.gui.svg"

OUT_DEB="${REPO_DIR}/${PKG_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb -Zxz --build "${PKG_ROOT}" "${OUT_DEB}" >/dev/null

echo "Built package: ${OUT_DEB}"
