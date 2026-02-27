"""Main application window."""

import csv
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

    content_scroller = Gtk.ScrolledWindow()
    content_scroller.set_vexpand(True)
    content_scroller.set_hexpand(True)
    content_scroller.set_child(container)

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

    phases_title = Gtk.Label(label="Execution phases")
    phases_title.set_xalign(0)
    phases_title.add_css_class("dim-label")
    self.phase_overall_bar = Gtk.ProgressBar()
    self.phase_overall_bar.set_hexpand(True)
    self.phase_overall_bar.set_show_text(True)
    self.validation_label = Gtk.Label(label="")
    self.validation_label.set_xalign(0)
    self.validation_label.add_css_class("error")

    summary_title = Gtk.Label(label="Execution summary")
    summary_title.set_xalign(0)
    summary_title.add_css_class("dim-label")
    self.summary_time_label = Gtk.Label(label="Time: 00:00")
    self.summary_time_label.set_xalign(0)
    self.summary_status_label = Gtk.Label(label="Status: Ready")
    self.summary_status_label.set_xalign(0)
    self.summary_keys_label = Gtk.Label(label="Keys detected: None")
    self.summary_keys_label.set_xalign(0)
    summary_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
    summary_row.append(self.summary_time_label)
    summary_row.append(self.summary_status_label)
    summary_row.append(self.summary_keys_label)

    self.results_grid = Gtk.Grid()
    self.results_grid.set_column_spacing(18)
    self.results_grid.set_row_spacing(6)

    results_scroller = Gtk.ScrolledWindow()
    results_scroller.set_min_content_height(180)
    results_scroller.set_vexpand(True)
    results_scroller.set_hexpand(True)
    results_scroller.set_child(self.results_grid)

    export_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    self.export_keys_txt_button = Gtk.Button(label="Export keys (.txt)")
    self.export_keys_txt_button.connect("clicked", self._on_export_keys_txt_clicked)
    self.export_keys_csv_button = Gtk.Button(label="Export keys (.csv)")
    self.export_keys_csv_button.connect("clicked", self._on_export_keys_csv_clicked)
    export_actions.append(self.export_keys_txt_button)
    export_actions.append(self.export_keys_csv_button)

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
    output_scroller.set_min_content_height(180)
    output_scroller.set_child(self.output_view)

    tabs_stack = Gtk.Stack()
    tabs_stack.set_vexpand(True)
    tabs_stack.set_hexpand(True)

    results_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    results_tab.set_vexpand(True)
    results_tab.set_hexpand(True)
    results_tab.append(results_scroller)
    results_tab.append(export_actions)
    tabs_stack.add_titled(results_tab, "results", "Results")

    logs_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    logs_tab.set_vexpand(True)
    logs_tab.set_hexpand(True)
    logs_tab.append(output_scroller)
    tabs_stack.add_titled(logs_tab, "logs", "Logs")

    tabs_switcher = Gtk.StackSwitcher()
    tabs_switcher.set_stack(tabs_stack)

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
    container.append(phases_title)
    container.append(self.phase_overall_bar)
    container.append(self.validation_label)
    container.append(summary_title)
    container.append(summary_row)
    container.append(tabs_switcher)
    container.append(tabs_stack)
    container.append(actions)

    root.append(content_scroller)
    self.set_content(root)
    self._connect_validation_signals()
    self._update_validation_state()
    self._refresh_phase_bars()
    self._refresh_summary()
    self._refresh_sector_keys_table()

  def _on_start_clicked(self, _button: Gtk.Button) -> None:
    is_valid, validation_error = self._validate_form()
    if not is_valid:
      self._refresh_status("Error")
      self.validation_label.set_label(validation_error)
      return

    params = self._build_params_from_form()
    status = self.controller.start_attack(params)
    self._refresh_status(status)
    self._sync_action_buttons()
    if self.controller.state.is_running:
      self._clear_output_view()
      self._refresh_sector_keys_table()
      self._start_runtime_polling()

  def _on_cancel_clicked(self, _button: Gtk.Button) -> None:
    status = self.controller.cancel_attack()
    self._refresh_status(status)
    self._sync_action_buttons()
    self._start_runtime_polling()

  def _refresh_status(self, status: str) -> None:
    _ = status
    self._refresh_phase_bars()
    self._refresh_summary()

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

    self._refresh_phase_bars()
    self._refresh_summary()
    self._refresh_sector_keys_table()
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

  def _refresh_phase_bars(self) -> None:
    phase_index = self.controller.state.phase_index
    phase_count = self.controller.state.phase_count
    phase_name = self.controller.state.phase_name

    if phase_index < 0 or phase_count < 1:
      self.phase_overall_bar.set_fraction(0.0)
      self.phase_overall_bar.set_text("Phases: idle")
      return

    overall_fraction = self.controller.current_phase_overall_fraction()
    phase_pos = phase_index + 1
    self.phase_overall_bar.set_fraction(overall_fraction)
    self.phase_overall_bar.set_text(
      f"Phase {phase_pos}/{phase_count}: {phase_name} ({overall_fraction * 100:.1f}%)"
    )

  def _refresh_summary(self) -> None:
    duration_text = self._format_duration(self.controller.current_duration_seconds())
    self.summary_time_label.set_label(f"Time: {duration_text}")
    self.summary_status_label.set_label(f"Status: {self.controller.current_status()}")
    count = self._count_detected_keys()
    self.summary_keys_label.set_label(f"Keys detected: {count}")

  def _format_duration(self, total_seconds: float) -> str:
    total = int(total_seconds)
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
      return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

  def _refresh_sector_keys_table(self) -> None:
    child = self.results_grid.get_first_child()
    while child is not None:
      next_child = child.get_next_sibling()
      self.results_grid.remove(child)
      child = next_child

    headers = ("Sector", "Key A", "Key B")
    for column, header_text in enumerate(headers):
      header_label = Gtk.Label(label=header_text)
      header_label.set_xalign(0)
      header_label.add_css_class("heading")
      self.results_grid.attach(header_label, column, 0, 1, 1)

    rows = self.controller.state.sector_keys
    if not rows:
      empty_label = Gtk.Label(label="No sector/key data yet.")
      empty_label.set_xalign(0)
      empty_label.add_css_class("dim-label")
      self.results_grid.attach(empty_label, 0, 1, 3, 1)
      self.export_keys_txt_button.set_sensitive(False)
      self.export_keys_csv_button.set_sensitive(False)
      return

    for row_index, sector in enumerate(sorted(rows.keys()), start=1):
      values = rows[sector]
      key_a = values.get("A", "") or "-"
      key_b = values.get("B", "") or "-"
      row_values = (str(sector), key_a, key_b)
      for column, cell_text in enumerate(row_values):
        cell_label = Gtk.Label(label=cell_text)
        cell_label.set_xalign(0)
        cell_label.set_selectable(True)
        self.results_grid.attach(cell_label, column, row_index, 1, 1)

    self.export_keys_txt_button.set_sensitive(True)
    self.export_keys_csv_button.set_sensitive(True)

  def _count_detected_keys(self) -> int:
    if self.controller.state.sector_keys:
      total = 0
      for values in self.controller.state.sector_keys.values():
        if values.get("A"):
          total += 1
        if values.get("B"):
          total += 1
      return total
    return len(self.controller.state.detected_keys)

  def _on_export_keys_txt_clicked(self, _button: Gtk.Button) -> None:
    rows = self.controller.state.sector_keys
    if not rows:
      self.validation_label.set_label("No keys available to export.")
      return

    self._open_keys_export_chooser("txt")

  def _on_export_keys_csv_clicked(self, _button: Gtk.Button) -> None:
    rows = self.controller.state.sector_keys
    if not rows:
      self.validation_label.set_label("No keys available to export.")
      return

    self._open_keys_export_chooser("csv")

  def _open_keys_export_chooser(self, format_name: str) -> None:
    output_file = self.output_entry.get_text().strip()
    base_name = f"recovered_keys.{format_name}"
    parent_path: Path | None = None
    if output_file:
      target = Path(output_file)
      base_name = f"{target.stem}_keys.{format_name}"
      parent_path = target.parent

    chooser = Gtk.FileChooserNative.new(
      f"Export keys as .{format_name}",
      self,
      Gtk.FileChooserAction.SAVE,
      "_Save",
      "_Cancel",
    )
    chooser.set_current_name(base_name)
    if parent_path is not None and parent_path.exists():
      chooser.set_current_folder(Gio.File.new_for_path(str(parent_path)))
    chooser.connect("response", self._on_export_chooser_response, format_name)
    self._active_chooser = chooser
    chooser.show()

  def _on_export_chooser_response(
    self,
    chooser: Gtk.FileChooserNative,
    response: int,
    format_name: str,
  ) -> None:
    if response != Gtk.ResponseType.ACCEPT:
      chooser.destroy()
      self._active_chooser = None
      return

    file_obj = chooser.get_file()
    if file_obj is None:
      chooser.destroy()
      self._active_chooser = None
      return

    file_path = file_obj.get_path()
    if not file_path:
      chooser.destroy()
      self._active_chooser = None
      return

    target_path = Path(file_path)
    if target_path.suffix.lower() != f".{format_name}":
      target_path = target_path.with_suffix(f".{format_name}")

    if format_name == "txt":
      self._write_keys_txt(target_path)
    else:
      self._write_keys_csv(target_path)

    chooser.destroy()
    self._active_chooser = None

  def _write_keys_txt(self, txt_path: Path) -> None:
    rows = self.controller.state.sector_keys
    keys: list[str] = []
    for sector in sorted(rows.keys()):
      values = rows[sector]
      key_a = values.get("A", "")
      key_b = values.get("B", "")
      if key_a:
        keys.append(key_a)
      if key_b:
        keys.append(key_b)

    try:
      txt_path.write_text("\n".join(keys) + "\n", encoding="utf-8")
      self.validation_label.set_label(f"Keys exported: {txt_path}")
    except OSError as exc:
      self.validation_label.set_label(f"TXT export failed: {exc}")

  def _write_keys_csv(self, csv_path: Path) -> None:
    rows = self.controller.state.sector_keys
    try:
      with csv_path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(["sector", "key_a", "key_b"])
        for sector in sorted(rows.keys()):
          values = rows[sector]
          writer.writerow([sector, values.get("A", ""), values.get("B", "")])
      self.validation_label.set_label(f"Keys exported: {csv_path}")
    except OSError as exc:
      self.validation_label.set_label(f"CSV export failed: {exc}")
