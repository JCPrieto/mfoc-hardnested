"""Main application window."""

from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from controller.app_controller import AppController
from models.execution_params import ExecutionParams


class MainWindow(Adw.ApplicationWindow):
  """Top-level window for the GUI bootstrap."""

  def __init__(
    self,
    application: Adw.Application,
    controller: AppController,
    width: int,
    height: int,
  ) -> None:
    super().__init__(application=application, title="MFOC Hardnested GUI")
    self.set_default_size(width, height)
    self.controller = controller
    self._active_chooser: Gtk.FileChooserNative | None = None
    self._runtime_timer_id: int | None = None

    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

    header = Adw.HeaderBar()
    header.set_title_widget(Gtk.Label(label="MFOC Hardnested"))
    root.append(header)

    container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    container.set_margin_top(24)
    container.set_margin_bottom(24)
    container.set_margin_start(24)
    container.set_margin_end(24)

    description = Gtk.Label(
      label="Set essential execution parameters and start the run."
    )
    description.set_xalign(0)
    description.add_css_class("dim-label")

    form = Gtk.Grid()
    form.set_column_spacing(12)
    form.set_row_spacing(8)

    self.output_entry = self._add_file_row(
      form=form,
      row=0,
      label="Output file (-O)",
      placeholder="Select output file...",
      action=Gtk.FileChooserAction.SAVE,
    )
    self.probes_entry = self._add_text_row(
      form=form,
      row=1,
      label="Probes per sector (-P)",
      placeholder="150",
      default="150",
    )
    self.tolerance_entry = self._add_text_row(
      form=form,
      row=2,
      label="Nonce tolerance (-T)",
      placeholder="20",
      default="20",
    )
    self.key_entry = self._add_text_row(
      form=form,
      row=3,
      label="Extra key hex (-k)",
      placeholder="ffffffffffff",
    )
    self.key_file_entry = self._add_file_row(
      form=form,
      row=4,
      label="Keys file (-f)",
      placeholder="Select keys file...",
      action=Gtk.FileChooserAction.OPEN,
    )

    self.skip_defaults_check = Gtk.CheckButton(label="Skip default keys (-C)")
    self.force_hardnested_check = Gtk.CheckButton(label="Force hardnested (-F)")
    self.reduce_memory_check = Gtk.CheckButton(label="Reduce memory usage (-Z)")

    flags_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    flags_box.append(self.skip_defaults_check)
    flags_box.append(self.force_hardnested_check)
    flags_box.append(self.reduce_memory_check)

    self.status_label = Gtk.Label(label=f"Status: {self.controller.current_status()}")
    self.status_label.set_xalign(0)
    self.progress_bar = Gtk.ProgressBar()
    self.progress_bar.set_hexpand(True)
    self.progress_bar.set_show_text(True)
    self.progress_bar.set_pulse_step(0.08)
    self.validation_label = Gtk.Label(label="")
    self.validation_label.set_xalign(0)
    self.validation_label.add_css_class("error")

    output_title = Gtk.Label(label="Process output")
    output_title.set_xalign(0)
    output_title.add_css_class("dim-label")

    self.output_view = Gtk.TextView()
    self.output_view.set_editable(False)
    self.output_view.set_cursor_visible(False)
    self.output_view.set_monospace(True)
    self.output_view.set_wrap_mode(Gtk.WrapMode.NONE)
    self.output_view.set_vexpand(True)
    self.output_view.set_hexpand(True)
    self._output_buffer = self.output_view.get_buffer()
    self._tag_meta = self._output_buffer.create_tag("meta", foreground="#6b7280")
    self._tag_stdout = self._output_buffer.create_tag("stdout")
    self._tag_stderr = self._output_buffer.create_tag("stderr", foreground="#b91c1c")

    output_scroller = Gtk.ScrolledWindow()
    output_scroller.set_vexpand(True)
    output_scroller.set_hexpand(True)
    output_scroller.set_child(self.output_view)

    actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    self.start_button = Gtk.Button(label="Start")
    self.start_button.add_css_class("suggested-action")
    self.start_button.connect("clicked", self._on_start_clicked)

    self.cancel_button = Gtk.Button(label="Cancel")
    self.cancel_button.connect("clicked", self._on_cancel_clicked)

    actions.append(self.start_button)
    actions.append(self.cancel_button)

    container.append(description)
    container.append(form)
    container.append(flags_box)
    container.append(self.status_label)
    container.append(self.progress_bar)
    container.append(self.validation_label)
    container.append(output_title)
    container.append(output_scroller)
    container.append(actions)

    root.append(container)
    self.set_content(root)
    self._connect_validation_signals()
    self._update_validation_state()
    self._refresh_progress()

  def _on_start_clicked(self, _button: Gtk.Button) -> None:
    is_valid, validation_error = self._validate_form()
    if not is_valid:
      self._refresh_status("Validation error")
      self.validation_label.set_label(validation_error)
      return

    params = self._build_params_from_form()
    status = self.controller.start_attack(params)
    self._refresh_status(status)
    self._sync_action_buttons()
    if self.controller.state.is_running:
      self._clear_output_view()
      self._start_runtime_polling()

  def _on_cancel_clicked(self, _button: Gtk.Button) -> None:
    status = self.controller.cancel_attack()
    self._refresh_status(status)
    self._sync_action_buttons()
    self._start_runtime_polling()

  def _refresh_status(self, status: str) -> None:
    self.status_label.set_label(f"Status: {status}")
    self._refresh_progress()

  def _add_text_row(
    self,
    form: Gtk.Grid,
    row: int,
    label: str,
    placeholder: str,
    default: str = "",
  ) -> Gtk.Entry:
    label_widget = Gtk.Label(label=label)
    label_widget.set_xalign(0)
    entry = Gtk.Entry()
    entry.set_hexpand(True)
    entry.set_placeholder_text(placeholder)
    if default:
      entry.set_text(default)
    form.attach(label_widget, 0, row, 1, 1)
    form.attach(entry, 1, row, 1, 1)
    return entry

  def _add_file_row(
    self,
    form: Gtk.Grid,
    row: int,
    label: str,
    placeholder: str,
    action: Gtk.FileChooserAction,
  ) -> Gtk.Entry:
    label_widget = Gtk.Label(label=label)
    label_widget.set_xalign(0)

    row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    entry = Gtk.Entry()
    entry.set_hexpand(True)
    entry.set_placeholder_text(placeholder)
    entry.set_editable(False)

    browse_button = Gtk.Button(label="Browse...")
    browse_button.connect("clicked", self._on_browse_file, entry, action)

    row_box.append(entry)
    row_box.append(browse_button)

    form.attach(label_widget, 0, row, 1, 1)
    form.attach(row_box, 1, row, 1, 1)
    return entry

  def _on_browse_file(
    self,
    _button: Gtk.Button,
    target_entry: Gtk.Entry,
    action: Gtk.FileChooserAction,
  ) -> None:
    title = "Select file"
    accept_label = "_Select"
    if action == Gtk.FileChooserAction.SAVE:
      title = "Select output file"
      accept_label = "_Save"
    elif action == Gtk.FileChooserAction.OPEN:
      title = "Select keys file"

    chooser = Gtk.FileChooserNative.new(
      title,
      self,
      action,
      accept_label,
      "_Cancel",
    )
    if action == Gtk.FileChooserAction.SAVE:
      chooser.set_current_name("dump.mfd")
      current_path = target_entry.get_text().strip()
      if current_path:
        parent = Path(current_path).parent
        chooser.set_current_folder(Gio.File.new_for_path(str(parent)))

    chooser.connect("response", self._on_file_chooser_response, target_entry)
    self._active_chooser = chooser
    chooser.show()

  def _on_file_chooser_response(
    self,
    chooser: Gtk.FileChooserNative,
    response: int,
    target_entry: Gtk.Entry,
  ) -> None:
    if response == Gtk.ResponseType.ACCEPT:
      file_obj = chooser.get_file()
      if file_obj is not None:
        path = file_obj.get_path()
        if path:
          target_entry.set_text(path)
          self._update_validation_state()
    chooser.destroy()
    self._active_chooser = None

  def _build_params_from_form(self) -> ExecutionParams:
    return ExecutionParams(
      output_file=self.output_entry.get_text().strip(),
      probes_per_sector=self._parse_int(self.probes_entry.get_text(), fallback=150),
      nonce_tolerance=self._parse_int(self.tolerance_entry.get_text(), fallback=20),
      extra_key_hex=self.key_entry.get_text().strip(),
      keys_file=self.key_file_entry.get_text().strip(),
      skip_default_keys=self.skip_defaults_check.get_active(),
      force_hardnested=self.force_hardnested_check.get_active(),
      reduce_memory=self.reduce_memory_check.get_active(),
    )

  def _parse_int(self, value: str, fallback: int) -> int:
    try:
      return int(value)
    except ValueError:
      return fallback

  def _connect_validation_signals(self) -> None:
    self.probes_entry.connect("changed", self._on_form_changed)
    self.tolerance_entry.connect("changed", self._on_form_changed)
    self.key_entry.connect("changed", self._on_form_changed)

  def _on_form_changed(self, _widget: Gtk.Widget) -> None:
    self._update_validation_state()

  def _update_validation_state(self) -> None:
    is_valid, message = self._validate_form()
    self.validation_label.set_label("" if is_valid else message)
    self._sync_action_buttons()

  def _sync_action_buttons(self) -> None:
    is_valid, _ = self._validate_form()
    can_start = is_valid and not self.controller.state.is_running
    self.start_button.set_sensitive(can_start)
    self.cancel_button.set_sensitive(self.controller.state.is_running)

  def _validate_form(self) -> tuple[bool, str]:
    output_file = self.output_entry.get_text().strip()
    if not output_file:
      return False, "Output file is required."

    output_parent = Path(output_file).parent
    if str(output_parent) and not output_parent.exists():
      return False, "Output folder does not exist."

    probes = self.probes_entry.get_text().strip()
    if not probes.isdigit():
      return False, "Probes per sector must be an integer."
    probes_value = int(probes)
    if probes_value < 1 or probes_value > 1000:
      return False, "Probes per sector must be between 1 and 1000."

    tolerance = self.tolerance_entry.get_text().strip()
    if not tolerance.isdigit():
      return False, "Nonce tolerance must be an integer."
    tolerance_value = int(tolerance)
    if tolerance_value < 1 or tolerance_value > 1000:
      return False, "Nonce tolerance must be between 1 and 1000."

    key_hex = self.key_entry.get_text().strip()
    if key_hex:
      if len(key_hex) != 12:
        return False, "Extra key hex must contain 12 hex characters."
      if not all(char in "0123456789abcdefABCDEF" for char in key_hex):
        return False, "Extra key hex must be hexadecimal."

    keys_file = self.key_file_entry.get_text().strip()
    if keys_file and not Path(keys_file).is_file():
      return False, "Keys file does not exist."

    return True, ""

  def _start_runtime_polling(self) -> None:
    if self._runtime_timer_id is None:
      self._runtime_timer_id = GLib.timeout_add(150, self._on_runtime_tick)

  def _on_runtime_tick(self) -> bool:
    lines, status_update = self.controller.poll_runtime()
    if lines:
      self._append_output_lines(lines)
    if status_update:
      self._refresh_status(status_update)

    self._refresh_progress()
    self._sync_action_buttons()

    keep_polling = self.controller.state.is_running or self.controller.has_pending_output()
    if not keep_polling:
      self._runtime_timer_id = None
    return keep_polling

  def _append_output_lines(self, lines: list[tuple[str, str]]) -> None:
    for stream_name, text in lines:
      timestamp = datetime.now().strftime("%H:%M:%S")
      level = "STDERR" if stream_name == "stderr" else "STDOUT"
      prefix = f"[{timestamp}] [{level}] "
      end_iter = self._output_buffer.get_end_iter()
      self._output_buffer.insert_with_tags(end_iter, prefix, self._tag_meta)

      end_iter = self._output_buffer.get_end_iter()
      if stream_name == "stderr":
        self._output_buffer.insert_with_tags(end_iter, text, self._tag_stderr)
      else:
        self._output_buffer.insert_with_tags(end_iter, text, self._tag_stdout)

      end_iter = self._output_buffer.get_end_iter()
      self._output_buffer.insert(end_iter, "\n")

    mark = self._output_buffer.create_mark(None, self._output_buffer.get_end_iter(), False)
    self.output_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

  def _clear_output_view(self) -> None:
    self._output_buffer.set_text("")

  def _refresh_progress(self) -> None:
    if self.controller.state.is_running:
      if self.controller.state.progress_determinate:
        fraction = max(0.0, min(1.0, self.controller.state.progress_fraction))
        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text(f"{fraction * 100:.1f}%")
      else:
        self.progress_bar.pulse()
        self.progress_bar.set_text("Working...")
      return

    if self.controller.state.status_text == "Finished":
      self.progress_bar.set_fraction(1.0)
      self.progress_bar.set_text("100%")
      return

    self.progress_bar.set_fraction(0.0)
    self.progress_bar.set_text("Idle")
