#!/usr/bin/env python3
"""GTK4/libadwaita entry point for the GUI prototype."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from controller.app_controller import AppController
from models.app_config import load_or_create_config, runtime_dir
from models.app_state import AppState
from runner.app_logging import configure_logging
from runner.mfoc_runner import MfocRunner
from ui.main_window import MainWindow


class MfocGuiApp(Adw.Application):
  """Application bootstrap and dependency wiring."""

  def __init__(self) -> None:
    super().__init__(application_id="io.github.mfoc.hardnested.gui")
    self.config = load_or_create_config()
    self.logger = configure_logging(runtime_dir(), self.config.log_level)

  def do_activate(self) -> None:
    state = AppState()
    runner = MfocRunner(binary_path=self.config.binary_path, logger=self.logger)
    controller = AppController(state=state, runner=runner, logger=self.logger)
    try:
      window = MainWindow(
        application=self,
        controller=controller,
        width=self.config.window_width,
        height=self.config.window_height,
      )
    except RuntimeError as exc:
      self.logger.exception("GTK startup failed")
      print(f"GTK startup failed: {exc}")
      self.quit()
      return

    self.logger.info("Main window presented")
    window.present()


def main() -> int:
  initialized = Gtk.init_check()
  if not initialized:
    print("GTK initialization failed: run this app inside a graphical session.")
    return 1

  app = MfocGuiApp()
  return app.run(None)


if __name__ == "__main__":
  raise SystemExit(main())
