"""In-memory state for the GUI session."""

from dataclasses import dataclass, field
from typing import Literal

AppStatus = Literal["ready", "running", "finished", "error"]


@dataclass
class AppState:
  """Mutable app state for basic workflow control."""

  is_running: bool = False
  status: AppStatus = "ready"
  status_detail: str = ""
  execution_started_at: float | None = None
  execution_ended_at: float | None = None
  detected_keys: list[str] = field(default_factory=list)
  estimated_key_attempts_total: int = 0
  processed_key_attempts: int = 0
  phase_name: str = "Idle"
  phase_index: int = -1
  phase_count: int = 4
  phase_progress_determinate: bool = False
  phase_progress_fraction: float = 0.0
