#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./gui/install-local.sh [--no-desktop] [--backend-bin /path/to/backend]

Options:
  --no-desktop              Skip .desktop/icon installation
  --backend-bin <path>      Backend executable path

Env:
  MFOC_BACKEND_BIN          Backend executable path (same as --backend-bin)
EOF
}

INSTALL_DESKTOP=1
BACKEND_BIN="${MFOC_BACKEND_BIN:-}"
while [[ $# -gt 0 ]]; do
  arg="$1"
  case "$arg" in
    --no-desktop)
      INSTALL_DESKTOP=0
      shift
      ;;
    --backend-bin)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --backend-bin" >&2
        usage >&2
        exit 2
      fi
      BACKEND_BIN="$2"
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
GUI_DIR="${REPO_DIR}/gui"

resolve_backend_from_config() {
  if [[ ! -f "${GUI_DIR}/runtime/config.json" ]]; then
    return 1
  fi

  python3 - <<'PY'
import json
from pathlib import Path

path = Path("runtime/config.json")
try:
  data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
  raise SystemExit(1)

value = str(data.get("binary_path", "")).strip()
if not value:
  raise SystemExit(1)
print(value)
PY
}

resolve_backend_auto() {
  local candidate=""

  # 1) Existing configured value.
  if candidate="$(resolve_backend_from_config 2>/dev/null)"; then
    if [[ -x "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  fi

  # 2) Local build in this repository.
  candidate="${REPO_DIR}/src/mfoc-hardnested"
  if [[ -x "${candidate}" ]]; then
    echo "${candidate}"
    return 0
  fi

  # 3) Typical install locations from `make install` / distro packages.
  for candidate in \
    "/usr/local/bin/mfoc-hardnested" \
    "/usr/bin/mfoc-hardnested" \
    "/opt/homebrew/bin/mfoc-hardnested"
  do
    if [[ -x "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done

  # 4) Common command names in PATH.
  for cmd in mfoc-hardnested mfoc; do
    if command -v "${cmd}" >/dev/null 2>&1; then
      command -v "${cmd}"
      return 0
    fi
  done

  return 1
}

echo "[1/5] Checking required commands..."
for cmd in python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
done

echo "[2/5] Checking GTK/libadwaita Python bindings..."
python3 - <<'PY'
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw  # noqa: F401
print("Bindings OK: Gtk 4 + libadwaita")
PY

echo "[3/5] Resolving backend binary..."
if [[ -z "${BACKEND_BIN}" ]]; then
  if ! BACKEND_BIN="$(resolve_backend_auto)"; then
    cat >&2 <<EOF
Could not auto-detect a backend executable.

Provide one explicitly:
  ./gui/install-local.sh --backend-bin /absolute/path/to/backend
  MFOC_BACKEND_BIN=/absolute/path/to/backend ./gui/install-local.sh
EOF
    exit 1
  fi
fi

if [[ ! -x "${BACKEND_BIN}" ]]; then
  cat >&2 <<EOF
Configured backend is not executable:
  ${BACKEND_BIN}

Provide a valid backend with one of:
  ./gui/install-local.sh --backend-bin /absolute/path/to/backend
  MFOC_BACKEND_BIN=/absolute/path/to/backend ./gui/install-local.sh
EOF
  exit 1
fi

echo "[4/5] Initializing GUI runtime config..."
cd "${GUI_DIR}"
python3 - "${BACKEND_BIN}" <<'PY'
import json
import sys
from models.app_config import load_or_create_config, config_path

backend_bin = sys.argv[1]
cfg = load_or_create_config()
cfg.binary_path = backend_bin
config_path().write_text(json.dumps(cfg.__dict__, indent=2) + "\n", encoding="utf-8")
print(f"Config ready: {config_path()}")
print(f"Backend path: {cfg.binary_path}")
PY

if [[ "${INSTALL_DESKTOP}" -eq 1 ]]; then
  echo "[5/5] Installing desktop launcher..."
  "${GUI_DIR}/install-desktop.sh"
else
  echo "[5/5] Skipping desktop launcher (--no-desktop)."
fi

cat <<EOF

Local installation complete.
Run GUI with:
  ./gui/main.py
EOF
