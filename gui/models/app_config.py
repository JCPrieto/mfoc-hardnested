"""Persistent app configuration."""

import os
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil


@dataclass
class AppConfig:
  """Minimal runtime settings."""

  binary_path: str
  log_level: str = "INFO"
  window_width: int = 900
  window_height: int = 540


def runtime_dir() -> Path:
  """Return runtime directory, preferring writable paths.

  Order:
  1) MFOC_GUI_RUNTIME_DIR (if set)
  2) app-local runtime dir when app tree is writable
  3) XDG state dir (~/.local/state/mfoc-hardnested-gui)
  """
  override = os.environ.get("MFOC_GUI_RUNTIME_DIR", "").strip()
  if override:
    return Path(override).expanduser().resolve()

  local_runtime = app_root() / "runtime"
  if os.access(app_root(), os.W_OK):
    return local_runtime

  state_home = os.environ.get("XDG_STATE_HOME", "~/.local/state")
  return (Path(state_home).expanduser() / "mfoc-hardnested-gui").resolve()


def app_root() -> Path:
  """Return application root path."""
  return Path(__file__).resolve().parents[1]


def default_binary_path() -> str:
  """Return best-effort backend binary path."""
  env_backend = os.environ.get("MFOC_BACKEND_BIN", "").strip()
  if env_backend:
    return str(Path(env_backend).expanduser())

  local_candidate = (app_root().parent / "src" / "mfoc-hardnested").resolve()
  if local_candidate.exists():
    return str(local_candidate)

  path_backend = shutil.which("mfoc-hardnested")
  if path_backend:
    return path_backend

  for candidate in ("/usr/local/bin/mfoc-hardnested", "/usr/bin/mfoc-hardnested"):
    if Path(candidate).exists():
      return candidate

  return str(local_candidate)


def config_path() -> Path:
  """Return config file path."""
  return runtime_dir() / "config.json"


def _normalize_binary_path(raw_path: str) -> str:
  path = Path(raw_path)
  if path.is_absolute():
    return str(path)
  return str((app_root().parent / path).resolve())


def load_or_create_config() -> AppConfig:
  """Load config from disk or create a default one."""
  path = config_path()
  path.parent.mkdir(parents=True, exist_ok=True)

  if not path.exists():
    config = AppConfig(binary_path=default_binary_path())
    path.write_text(json.dumps(asdict(config), indent=2) + "\n", encoding="utf-8")
    return config

  raw_data = json.loads(path.read_text(encoding="utf-8"))
  config = AppConfig(
    binary_path=_normalize_binary_path(raw_data.get("binary_path", default_binary_path())),
    log_level=raw_data.get("log_level", AppConfig.log_level),
    window_width=raw_data.get("window_width", AppConfig.window_width),
    window_height=raw_data.get("window_height", AppConfig.window_height),
  )
  path.write_text(json.dumps(asdict(config), indent=2) + "\n", encoding="utf-8")
  return config
