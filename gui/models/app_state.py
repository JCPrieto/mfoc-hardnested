"""In-memory state for the GUI session."""

from dataclasses import dataclass


@dataclass
class AppState:
  """Mutable app state for basic workflow control."""

  is_running: bool = False
  status_text: str = "Ready"
