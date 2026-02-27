"""Backend runner placeholder for mfoc-hardnested process execution."""

import logging
import os
from typing import TextIO
import queue
import signal
import subprocess
import threading

from models.execution_params import ExecutionParams


class MfocRunner:
  """Thin abstraction around backend command execution."""

  def __init__(self, binary_path: str, logger: logging.Logger) -> None:
    self.binary_path = binary_path
    self.logger = logger
    self._process: subprocess.Popen[str] | None = None
    self._output_queue: queue.Queue[tuple[str, str]] = queue.Queue()
    self._last_exit_code: int | None = None

  def start(self, params: ExecutionParams) -> tuple[bool, str]:
    """Start backend execution as a child process."""
    if self.is_running():
      return False, "Process already running."

    self.logger.info("Runner start requested (binary: %s)", self.binary_path)
    args = params.to_args()
    self.logger.info("Runner args: %s", " ".join(args))
    command = [self.binary_path, *args]
    self._last_exit_code = None
    self._clear_output_queue()

    try:
      self._process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        start_new_session=True,
      )
    except FileNotFoundError:
      self._process = None
      return False, f"Binary not found: {self.binary_path}"
    except PermissionError:
      self._process = None
      return False, f"Binary is not executable: {self.binary_path}"
    except OSError as exc:
      self._process = None
      return False, f"Failed to start process: {exc}"

    assert self._process.stdout is not None
    assert self._process.stderr is not None
    threading.Thread(
      target=self._reader_loop,
      args=("stdout", self._process.stdout),
      daemon=True,
    ).start()
    threading.Thread(
      target=self._reader_loop,
      args=("stderr", self._process.stderr),
      daemon=True,
    ).start()

    self.logger.info("Runner process started with PID %s", self._process.pid)
    return True, ""

  def cancel(self) -> tuple[bool, str]:
    """Cancel backend execution."""
    if not self.is_running():
      return False, "No active process."

    assert self._process is not None
    self.logger.info("Runner cancel requested for PID %s", self._process.pid)
    return_code: int | None = None

    try:
      os.killpg(self._process.pid, signal.SIGINT)
      return_code = self._process.wait(timeout=4)
      self.logger.info("Runner process terminated cleanly with SIGINT")
    except subprocess.TimeoutExpired:
      self.logger.warning("Runner ignored SIGINT; escalating to SIGTERM")
      os.killpg(self._process.pid, signal.SIGTERM)
      try:
        return_code = self._process.wait(timeout=3)
        self.logger.info("Runner process terminated with SIGTERM")
      except subprocess.TimeoutExpired:
        self.logger.warning("Runner ignored SIGTERM; forcing SIGKILL")
        os.killpg(self._process.pid, signal.SIGKILL)
        return_code = self._process.wait(timeout=3)
        self.logger.warning("Runner process forced to SIGKILL")
    except OSError as exc:
      self.logger.error("Runner cancel failed: %s", exc)
      return False, str(exc)
    finally:
      self._last_exit_code = return_code
      self._process = None

    return True, ""

  def is_running(self) -> bool:
    """Return whether the child process is currently running."""
    if self._process is None:
      return False

    return_code = self._process.poll()
    if return_code is None:
      return True

    self.logger.info("Runner process exited with code %s", return_code)
    self._last_exit_code = return_code
    self._process = None
    return False

  def drain_output(self) -> list[tuple[str, str]]:
    """Drain pending output lines from stdout/stderr readers."""
    lines: list[tuple[str, str]] = []
    while True:
      try:
        lines.append(self._output_queue.get_nowait())
      except queue.Empty:
        return lines

  def has_pending_output(self) -> bool:
    """Return whether there is buffered output waiting to be consumed."""
    return not self._output_queue.empty()

  def consume_exit_code(self) -> int | None:
    """Consume and clear the last known process exit code."""
    code = self._last_exit_code
    self._last_exit_code = None
    return code

  def _reader_loop(self, stream_name: str, pipe: TextIO) -> None:
    for line in iter(pipe.readline, ""):
      text = line.rstrip("\n")
      if text:
        self._output_queue.put((stream_name, text))
    pipe.close()

  def _clear_output_queue(self) -> None:
    while not self._output_queue.empty():
      try:
        self._output_queue.get_nowait()
      except queue.Empty:
        return
