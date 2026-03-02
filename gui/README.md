# GUI Skeleton

Initial GNOME-focused GUI bootstrap using GTK4 + libadwaita.

## Layout

- `ui/`: GTK/libadwaita views and widgets.
- `controller/`: UI orchestration and input validation.
- `runner/`: process execution and backend integration.
- `models/`: app state and data models.
- `main.py`: GUI entry point.

## Run

Install runtime dependencies on Ubuntu 22.04:

```bash
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

Start the GUI prototype:

```bash
./gui/main.py
```

## Runtime files

The app creates local runtime files under `gui/runtime/`:

- `gui/runtime/config.json`: minimal persisted settings.
- `gui/runtime/logs/gui.log`: local application log file.

## Execution form (day 2)

Current essential fields map to CLI options:

- `Output file (-O)`
- `Probes per sector (-P)`
- `Nonce tolerance (-T)`
- `Extra key hex (-k)`
- `Keys file (-f)`
- `Skip default keys (-C)`
- `Force hardnested (-F)`
- `Reduce memory usage (-Z)`

Basic validation is now active:

- `Output file (-O)` is required and its parent folder must exist.
- `Probes per sector (-P)` and `Nonce tolerance (-T)` must be integers in `[1, 1000]`.
- Default values are `-P 150` and `-T 20`.
- `Extra key hex (-k)` is optional, but if present must be 12 hex characters.
- `Keys file (-f)` is optional, but if present must exist.

Button behavior:

- `Start` is enabled only when form is valid and no run is active.
- `Cancel` is enabled only while a run is active.

Backend integration (current step):

- `Start` launches `mfoc-hardnested` as a child process (`subprocess.Popen`).
- `Cancel` sends termination to the process group (`SIGTERM`, then `SIGKILL` if needed).
- `stdout/stderr` are captured asynchronously and shown live in `Process output`.
- Each output line is prefixed with `[HH:MM:SS] [STDOUT|STDERR]`.
- `STDERR` lines are highlighted in red in the output view.

GNOME visual adjustments:

- Header uses `Adw.WindowTitle` with subtitle.
- Main content is centered with `Adw.Clamp` for desktop readability.
- UI blocks are grouped in card-like sections with subtle Adwaita styling.
- Summary values are shown as chips and actions are right-aligned.

## Desktop launcher

Install `.desktop` launcher + icon for the current user:

```bash
./gui/install-desktop.sh
```

This installs:

- `~/.local/share/applications/io.github.mfoc.hardnested.gui.desktop`
- `~/.local/share/icons/hicolor/scalable/apps/io.github.mfoc.hardnested.gui.svg`

Uninstall:

```bash
./gui/uninstall-local.sh
```

## Local installer

Run a complete local setup with checks:

```bash
./gui/install-local.sh
```

What it verifies:

- `python3` is available.
- GTK4/libadwaita Python bindings are importable.
- configured backend exists and is executable.
- runtime config is initialized.
- desktop launcher/icon is installed (unless `--no-desktop`).

If backend is not explicitly provided, auto-detection order is:

1. `binary_path` from `gui/runtime/config.json` (if executable).
2. `src/mfoc-hardnested` in the current repository (if executable).
3. Typical install paths: `/usr/local/bin/mfoc-hardnested`, `/usr/bin/mfoc-hardnested`.
4. `mfoc-hardnested` or `mfoc` available in `PATH`.

Optional:

```bash
./gui/install-local.sh --no-desktop
./gui/install-local.sh --backend-bin /absolute/path/to/mfoc-hardnested
MFOC_BACKEND_BIN=/absolute/path/to/mfoc-hardnested ./gui/install-local.sh
```
