# GUI Prototype

GNOME-focused GUI prototype using GTK4 + libadwaita.

## Layout

- `ui/`: GTK/libadwaita views and widgets.
- `controller/`: UI orchestration and validation.
- `runner/`: backend process execution.
- `models/`: app state and persisted config.
- `main.py`: GUI entry point.

## Run

Install runtime dependencies on Ubuntu:

```bash
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

Start the GUI from repository root:

```bash
./gui/main.py
```

## Runtime files

Runtime directory resolution order:

1. `MFOC_GUI_RUNTIME_DIR` (if set).
2. `gui/runtime/` (when application tree is writable).
3. `~/.local/state/mfoc-hardnested-gui/` (fallback).

Main runtime files:

- `config.json`: persisted settings (including backend binary path).
- `logs/gui.log`: application log file.

## Execution form

Current fields map to CLI options:

- `Output file (-O)`
- `Probes per sector (-P)` (default `150`)
- `Nonce tolerance (-T)` (default `20`)
- `Extra key hex (-k)`
- `Keys file (-f)`
- `Skip default keys (-C)`
- `Force hardnested (-F)`
- `Reduce memory usage (-Z)`

Validation:

- `Output file (-O)` is required and its parent folder must exist.
- `-P` and `-T` must be integers in `[1, 1000]`.
- `-k` is optional, but if provided must be exactly 12 hex characters.
- `-f` is optional, but if provided must exist.

Button state:

- `Start` is enabled only when form is valid and no run is active.
- `Cancel` is enabled only while a run is active.

## Backend execution behavior

- `Start` launches `mfoc-hardnested` via `subprocess.Popen`.
- Output from `stdout`/`stderr` is streamed live in the logs panel.
- Each line is prefixed with `[HH:MM:SS] [STDOUT|STDERR]`.
- `stderr` lines are highlighted in red.

Cancellation sends signals to the process group in this order:

1. `SIGINT`
2. `SIGTERM` (if still running)
3. `SIGKILL` (if still running)

## Backend path selection

Default backend resolution order:

1. `MFOC_BACKEND_BIN` env var (if set).
2. Repository-local `src/mfoc-hardnested` (if present).
3. `mfoc-hardnested` found in `PATH`.
4. `/usr/local/bin/mfoc-hardnested` or `/usr/bin/mfoc-hardnested`.

## Packaging/install scripts

Available scripts in this tree:

- `install-local.sh`: prepares runtime config and optional desktop launcher.
- `install-desktop.sh`: installs `.desktop` launcher and icon in `~/.local/share`.
- `uninstall-local.sh`: removes local desktop integration.
- `packaging/deb/build-deb.sh`: builds `mfoc-hardnested-gui_<version>_all.deb`.

Examples:

```bash
./gui/install-local.sh
./gui/install-local.sh --backend-bin /absolute/path/to/mfoc-hardnested
./gui/install-desktop.sh
./gui/uninstall-local.sh
./gui/packaging/deb/build-deb.sh
```

`gui/VERSION` is used by `build-deb.sh` as the first package version source.
