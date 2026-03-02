# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains all C sources and headers for the `mfoc-hardnested` binary.
- `src/hardnested/` holds SIMD and no-SIMD brute-force/bitarray implementations.
- `gui/` contains the GTK4/libadwaita frontend prototype (`main.py`, `ui/`, `controller/`, `runner/`, `models/`).
- `src/include/` and `src/lib/` contain bundled Windows-oriented headers and prebuilt libraries used by the Visual Studio build.
- Root build metadata lives in `configure.ac`, `Makefile.am`, and `m4/` (Autotools).
- Packaging and distribution files are under `debian/`; CI is in `.github/workflows/build.yml`.

## Build, Test, and Development Commands
- `autoreconf -vis` regenerates configure/build scripts.
- `./configure` detects platform features and dependencies (`libnfc`, `liblzma`, `pthread`, `libm`).
- `make` builds `src/mfoc-hardnested`.
- `make style` applies the repository C formatting profile (via `astyle`) and strips trailing whitespace.
- `make install` installs the binary and man page.
- `./src/mfoc-hardnested -h` is the baseline smoke test after compilation.
- `./gui/main.py` starts the GUI prototype (requires GTK4/libadwaita Python bindings).
- Optional containerized check: `docker build --build-arg COMPILER=gcc-8 .`.

## Coding Style & Naming Conventions
- Language standard is C99 (`configure.ac` sets `-std=c99`).
- Use 2-space indentation and Linux-style braces; run `make style` before submitting.
- Keep naming consistent with existing code:
  - files/functions: `lower_snake_case`
  - macros/constants: `UPPER_SNAKE_CASE`
  - type aliases ending in `_t` where already established.
- Prefer small, focused changes; keep SIMD-specific logic isolated in `src/hardnested/*`.

## Testing Guidelines
- There is no dedicated unit-test suite in this repository.
- Minimum validation for each change:
  - clean build (`autoreconf -vis && ./configure && make`)
  - runtime smoke check (`./src/mfoc-hardnested -h`)
  - for algorithm changes, include a reproducible hardware or benchmark validation note in the PR.

## Commit & Pull Request Guidelines
- Match existing history style: short, imperative commit subjects (for example, `Fix build on MacOS`, `Remove verbose logging`).
- Keep one logical change per commit.
- PRs should include:
  - clear summary and motivation
  - linked issue (if available)
  - platforms/toolchains tested
  - relevant command output for build/smoke validation.
