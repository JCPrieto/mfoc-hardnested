"""Controller layer between UI and runner."""

import logging

from models.app_state import AppState
from models.execution_params import ExecutionParams
from runner.mfoc_runner import MfocRunner


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
      return self.state.status_text

    started, error = self.runner.start(params)
    if not started:
      self.state.is_running = False
      self.state.status_text = f"Start failed: {error}"
      self.logger.error("Attack start failed: %s", error)
      return self.state.status_text

    self.state.is_running = True
    self.state.status_text = "Running..."
    self.logger.info("Attack state changed to running")
    return self.state.status_text

  def cancel_attack(self) -> str:
    self.sync_running_state()

    if not self.state.is_running:
      self.logger.info("Cancel requested while not running")
      return self.state.status_text

    cancelled, error = self.runner.cancel()
    if not cancelled:
      self.state.status_text = f"Cancel failed: {error}"
      self.logger.error("Attack cancel failed: %s", error)
      return self.state.status_text

    self.state.is_running = False
    self.state.status_text = "Cancelled"
    self.logger.info("Attack state changed to cancelled")
    return self.state.status_text

  def current_status(self) -> str:
    return self.state.status_text

  def sync_running_state(self) -> bool:
    """Refresh state.is_running from runner state."""
    self.state.is_running = self.runner.is_running()
    return self.state.is_running

  def poll_runtime(self) -> tuple[list[tuple[str, str]], str | None]:
    """Collect output lines and process lifecycle transitions."""
    lines: list[tuple[str, str]] = []
    for stream_name, text in self.runner.drain_output():
      lines.append((stream_name, text))

    status_update: str | None = None
    was_running = self.state.is_running
    is_running = self.runner.is_running()
    self.state.is_running = is_running

    if was_running and not is_running:
      if self.state.status_text != "Cancelled":
        exit_code = self.runner.consume_exit_code()
        if exit_code == 0:
          self.state.status_text = "Finished"
        else:
          self.state.status_text = f"Failed (exit {exit_code})"
        status_update = self.state.status_text
        self.logger.info("Attack finished with status: %s", self.state.status_text)

    return lines, status_update

  def has_pending_output(self) -> bool:
    """Return whether there are unread output lines."""
    return self.runner.has_pending_output()
