"""Controller layer between UI and runner."""

import logging
from pathlib import Path
import re
import time

from models.app_state import AppState, AppStatus
from models.execution_params import ExecutionParams
from runner.mfoc_runner import MfocRunner

_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_KEY_ATTEMPT_RE = re.compile(r"\[Key:\s*[0-9a-fA-F]{12}\]\s*->")
_KEY_PATTERNS = (
  re.compile(r"Key found:\s*([0-9a-fA-F]{12})"),
  re.compile(r"Found\s+Key\s+[AB]:\s*([0-9a-fA-F]{12})"),
  re.compile(r"revealed Key [AB]:\s*\[([0-9a-fA-F]{12})\]"),
)
_SECTOR_KEYS_RE = re.compile(
  r"Sector\s+(\d+)\s*-\s*(?:Found\s+Key\s+A:\s*([0-9A-Fa-f]{12})|Unknown\s+Key\s+A)\s*(?:Found\s+Key\s+B:\s*([0-9A-Fa-f]{12})|Unknown\s+Key\s+B)"
)
_DEFAULT_KEYS_COUNT = 13
_EXECUTION_PHASES = (
  "Authentication",
  "Key Recovery",
  "Hardnested Brute Force",
  "Dump",
)


class AppController:
  """Coordinates UI actions and app state."""

  def __init__(self, state: AppState, runner: MfocRunner, logger: logging.Logger) -> None:
    self.state = state
    self.runner = runner
    self.logger = logger

  def start_attack(self, params: ExecutionParams) -> str:
    self.sync_running_state()

    if self.state.is_running:
      self.logger.info("Start requested while already running")
      return self.current_status()

    started, error = self.runner.start(params)
    if not started:
      self.state.is_running = False
      self._set_status("error", error)
      self.logger.error("Attack start failed: %s", error)
      return self.current_status()

    self.state.is_running = True
    self._set_status("running")
    self.state.execution_started_at = time.monotonic()
    self.state.execution_ended_at = None
    self.state.detected_keys = []
    self.state.sector_keys = {}
    self.state.processed_key_attempts = 0
    self.state.estimated_key_attempts_total = self._estimate_key_attempts(params)
    self.state.phase_count = len(_EXECUTION_PHASES)
    self._set_phase(0)
    self.logger.info("Attack state changed to running")
    return self.current_status()

  def cancel_attack(self) -> str:
    self.sync_running_state()

    if not self.state.is_running:
      self.logger.info("Cancel requested while not running")
      return self.current_status()

    cancelled, error = self.runner.cancel()
    if not cancelled:
      self._set_status("error", error)
      self.logger.error("Attack cancel failed: %s", error)
      return self.current_status()

    self.state.is_running = False
    self._set_status("ready", "Cancelled")
    self.state.phase_progress_determinate = False
    self.state.phase_progress_fraction = 0.0
    self.state.execution_ended_at = time.monotonic()
    self.logger.info("Attack state changed to cancelled")
    return self.current_status()

  def current_status(self) -> str:
    labels: dict[AppStatus, str] = {
      "ready": "Ready",
      "running": "Running",
      "finished": "Finished",
      "error": "Error",
    }
    base = labels[self.state.status]
    if self.state.status_detail:
      return f"{base}: {self.state.status_detail}"
    return base

  def sync_running_state(self) -> bool:
    """Refresh state.is_running from runner state."""
    self.state.is_running = self.runner.is_running()
    return self.state.is_running

  def poll_runtime(self) -> tuple[list[tuple[str, str]], str | None]:
    """Collect output lines and process lifecycle transitions."""
    lines: list[tuple[str, str]] = []
    for stream_name, text in self.runner.drain_output():
      lines.append((stream_name, text))
      self._update_phase_from_output(text)
      self._update_phase_progress_from_output(text)
      self._update_summary_from_output(text)

    status_update: str | None = None
    was_running = self.state.is_running
    is_running = self.runner.is_running()
    self.state.is_running = is_running

    if was_running and not is_running:
      self.state.execution_ended_at = time.monotonic()
      if self.state.status == "running":
        exit_code = self.runner.consume_exit_code()
        if exit_code == 0:
          self._set_status("finished")
          self._set_phase(len(_EXECUTION_PHASES) - 1)
          self.state.phase_progress_determinate = True
          self.state.phase_progress_fraction = 1.0
        else:
          self._set_status("error", f"Exit {exit_code}")
        status_update = self.current_status()
        self.logger.info("Attack finished with status: %s", status_update)

    return lines, status_update

  def has_pending_output(self) -> bool:
    """Return whether there are unread output lines."""
    return self.runner.has_pending_output()

  def current_duration_seconds(self) -> float:
    if self.state.execution_started_at is None:
      return 0.0
    end_time = self.state.execution_ended_at
    if end_time is None:
      end_time = time.monotonic()
    return max(0.0, end_time - self.state.execution_started_at)

  def current_phase_overall_fraction(self) -> float:
    if self.state.phase_index < 0 or self.state.phase_count < 1:
      return 0.0
    base = self.state.phase_index / self.state.phase_count
    if self.state.phase_progress_determinate:
      base += self.state.phase_progress_fraction / self.state.phase_count
    return max(0.0, min(1.0, base))

  def _update_phase_progress_from_output(self, text: str) -> None:
    if _KEY_ATTEMPT_RE.search(text):
      self.state.processed_key_attempts += 1

    percent_match = _PERCENT_RE.search(text)
    if percent_match and self.state.phase_index >= 2:
      percent = float(percent_match.group(1))
      self.state.phase_progress_determinate = True
      self.state.phase_progress_fraction = max(0.0, min(1.0, percent / 100.0))
      return

    if self.state.phase_index <= 1 and self.state.estimated_key_attempts_total > 0 and self.state.processed_key_attempts > 0:
      fraction = self.state.processed_key_attempts / self.state.estimated_key_attempts_total
      self.state.phase_progress_determinate = True
      self.state.phase_progress_fraction = max(0.0, min(1.0, fraction))
      return

    if "Brute force phase completed" in text:
      self._set_phase(2)
      self.state.phase_progress_determinate = True
      self.state.phase_progress_fraction = 1.0

  def _update_phase_from_output(self, text: str) -> None:
    if "Try to authenticate to all sectors" in text or _KEY_ATTEMPT_RE.search(text):
      self._set_phase(0)
      return
    if "Checking for key reuse" in text or "Using sector" in text or "  Found Key: " in text:
      self._set_phase(1)
      return
    if (
      "Apply Sum property" in text
      or "Apply bit flip properties" in text
      or "Starting brute force..." in text
      or "Brute force phase" in text
    ):
      self._set_phase(2)
      return
    if "dumping keys to a file" in text or text.startswith("Block "):
      self._set_phase(3)
      return

  def _update_summary_from_output(self, text: str) -> None:
    for pattern in _KEY_PATTERNS:
      for match in pattern.finditer(text):
        key_value = match.group(1).upper()
        if key_value not in self.state.detected_keys:
          self.state.detected_keys.append(key_value)

    sector_match = _SECTOR_KEYS_RE.search(text)
    if not sector_match:
      return
    sector = int(sector_match.group(1))
    key_a = (sector_match.group(2) or "").upper()
    key_b = (sector_match.group(3) or "").upper()
    row = self.state.sector_keys.setdefault(sector, {"A": "", "B": ""})
    if key_a:
      row["A"] = key_a
    if key_b:
      row["B"] = key_b

  def _set_status(self, status: AppStatus, detail: str = "") -> None:
    self.state.status = status
    self.state.status_detail = detail

  def _set_phase(self, phase_index: int) -> None:
    if phase_index < 0 or phase_index >= len(_EXECUTION_PHASES):
      return
    if phase_index < self.state.phase_index:
      return
    if phase_index != self.state.phase_index:
      self.state.phase_progress_determinate = False
      self.state.phase_progress_fraction = 0.0
    self.state.phase_index = phase_index
    self.state.phase_name = _EXECUTION_PHASES[phase_index]

  def _estimate_key_attempts(self, params: ExecutionParams) -> int:
    total = 0
    if params.keys_file:
      total += self._count_lines(params.keys_file)
    if params.extra_key_hex:
      total += 1
    if not params.skip_default_keys:
      total += _DEFAULT_KEYS_COUNT
    return total

  def _count_lines(self, file_path: str) -> int:
    try:
      with Path(file_path).open("r", encoding="utf-8", errors="ignore") as file_obj:
        return sum(1 for _line in file_obj)
    except OSError as exc:
      self.logger.warning("Unable to count lines for key file %s: %s", file_path, exc)
      return 0
