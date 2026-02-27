"""Local logging setup for GUI runtime."""

import logging
from pathlib import Path


def configure_logging(base_dir: Path, level: str) -> logging.Logger:
  """Configure root logger with file and console handlers."""
  logs_dir = base_dir / "logs"
  logs_dir.mkdir(parents=True, exist_ok=True)
  log_file = logs_dir / "gui.log"

  logger = logging.getLogger("mfoc_gui")
  logger.setLevel(getattr(logging, level.upper(), logging.INFO))
  logger.handlers.clear()
  logger.propagate = False

  formatter = logging.Formatter(
    "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
  )

  file_handler = logging.FileHandler(log_file, encoding="utf-8")
  file_handler.setFormatter(formatter)
  logger.addHandler(file_handler)

  stream_handler = logging.StreamHandler()
  stream_handler.setFormatter(formatter)
  logger.addHandler(stream_handler)

  logger.info("Logging initialized at %s", log_file)
  return logger
