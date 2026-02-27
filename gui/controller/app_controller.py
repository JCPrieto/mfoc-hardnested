"""Controller layer between UI and runner."""

import logging
import re

from models.app_state import AppState, AppStatus
from models.execution_params import ExecutionParams
from runner.mfoc_runner import MfocRunner

_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


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
    self.state.progress_determinate = False
    self.state.progress_fraction = 0.0
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
    self.state.progress_determinate = False
    self.state.progress_fraction = 0.0
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
      self._update_progress_from_output(text)

    status_update: str | None = None
    was_running = self.state.is_running
    is_running = self.runner.is_running()
    self.state.is_running = is_running

    if was_running and not is_running:
      if self.state.status == "running":
        exit_code = self.runner.consume_exit_code()
        if exit_code == 0:
          self._set_status("finished")
          self.state.progress_determinate = True
          self.state.progress_fraction = 1.0
        else:
          self._set_status("error", f"Exit {exit_code}")
        status_update = self.current_status()
        self.logger.info("Attack finished with status: %s", status_update)

    return lines, status_update

  def has_pending_output(self) -> bool:
    """Return whether there are unread output lines."""
    return self.runner.has_pending_output()

  def _update_progress_from_output(self, text: str) -> None:
    percent_match = _PERCENT_RE.search(text)
    if percent_match:
      percent = float(percent_match.group(1))
      self.state.progress_determinate = True
      self.state.progress_fraction = max(0.0, min(1.0, percent / 100.0))
      return

    if "Brute force phase completed" in text:
      self.state.progress_determinate = True
      self.state.progress_fraction = 1.0

  def _set_status(self, status: AppStatus, detail: str = "") -> None:
    self.state.status = status
    self.state.status_detail = detail
