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
