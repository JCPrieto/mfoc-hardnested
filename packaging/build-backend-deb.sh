#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTRA_FLAGS=()

if [[ "${1:-}" == "--ignore-deps" ]]; then
  EXTRA_FLAGS+=("-d")
fi

if [[ ! -d "${REPO_DIR}/debian" ]]; then
  echo "debian/ directory not found at: ${REPO_DIR}" >&2
  exit 1
fi

if ! command -v dpkg-buildpackage >/dev/null 2>&1; then
  echo "dpkg-buildpackage is required." >&2
  exit 1
fi

if [[ "${#EXTRA_FLAGS[@]}" -eq 0 ]] && command -v dpkg-checkbuilddeps >/dev/null 2>&1; then
  set +e
  CHECK_OUTPUT="$(cd "${REPO_DIR}" && dpkg-checkbuilddeps 2>&1)"
  CHECK_EXIT=$?
  set -e
  if [[ ${CHECK_EXIT} -ne 0 ]]; then
    echo "Missing build dependencies for backend package:" >&2
    echo "${CHECK_OUTPUT}" >&2
    echo >&2
    echo "Install them with:" >&2
    echo "  sudo apt install -y debhelper libnfc-dev liblzma-dev pkg-config" >&2
    echo >&2
    echo "Or run with --ignore-deps to force dpkg-buildpackage -d." >&2
    exit 1
  fi
fi

echo "[1/2] Building backend Debian package (binary only)..."
(
  cd "${REPO_DIR}"
  dpkg-buildpackage -us -uc -b "${EXTRA_FLAGS[@]}"
)

echo "[2/2] Build completed. Artifacts:"
find "${REPO_DIR}/.." -maxdepth 1 -type f \
  \( -name "mfoc-hardnested_*.deb" -o -name "mfoc-hardnested_*.buildinfo" -o -name "mfoc-hardnested_*.changes" \) \
  -printf "%f\n" | sort
