"""Persistent app configuration."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass
class AppConfig:
  """Minimal runtime settings."""

  binary_path: str
  log_level: str = "INFO"
  window_width: int = 900
  window_height: int = 540


def runtime_dir() -> Path:
  """Return local runtime directory inside the repository."""
  return Path(__file__).resolve().parents[1] / "runtime"


def repo_root() -> Path:
  """Return repository root path."""
  return Path(__file__).resolve().parents[2]


def default_binary_path() -> str:
  """Return default backend binary path as absolute string."""
  return str((repo_root() / "src" / "mfoc-hardnested").resolve())


def config_path() -> Path:
  """Return config file path."""
  return runtime_dir() / "config.json"


def _normalize_binary_path(raw_path: str) -> str:
  path = Path(raw_path)
  if path.is_absolute():
    return str(path)
  return str((repo_root() / path).resolve())


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
