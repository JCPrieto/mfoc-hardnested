"""In-memory state for the GUI session."""

from dataclasses import dataclass
from typing import Literal

AppStatus = Literal["ready", "running", "finished", "error"]


@dataclass
class AppState:
  """Mutable app state for basic workflow control."""

  is_running: bool = False
  status: AppStatus = "ready"
  status_detail: str = ""
  progress_determinate: bool = False
  progress_fraction: float = 0.0
