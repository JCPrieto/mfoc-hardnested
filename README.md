MFOC is an open source implementation of the "offline nested" attack by Nethemba.
This fork also includes the "hardnested" attack by Carlo Meijer and Roel Verdult.

The program recovers authentication keys from MIFARE Classic cards.

MFOC can recover keys only if at least one known key is available:
- a default key (hardcoded in MFOC), or
- a custom key provided by the user through CLI options.

This repository includes:
- a Windows x64 build setup (Visual Studio + clang-cl), and
- a GNU/Linux Autotools build flow.

For credits, see `AUTHORS`.

Dependencies used by this project:
- `libnfc`: https://github.com/nfc-tools/libnfc/
- `libusb-win32`: https://sourceforge.net/projects/libusb-win32/files/libusb-win32-releases/1.2.6.0/
- `pthreads4w`: https://sourceforge.net/projects/pthreads4w/
- `liblzma`: https://tukaani.org/xz/

On the Visual Studio build path, prebuilt Windows-oriented libraries and headers are under `src/lib` and `src/include`.

# Build from source

Windows:
- Install Visual Studio 2019 with Desktop development with C++ and clang-cl toolchain support.
- Open `mfoc-hardnested.sln` and build.

Linux:
```bash
autoreconf -vis
./configure
make
sudo make install
```

## Debian packaging (backend)

This repository contains Debian packaging metadata under `debian/`.
From repository root, build with:

```bash
dpkg-buildpackage -us -uc -b
```

If dependencies are missing:

```bash
sudo apt install -y debhelper libnfc-dev liblzma-dev pkg-config
```

Note: there is currently no `./packaging/build-backend-deb.sh` script in this repository.

## GUI

The GUI lives in `gui/` (lowercase). See `gui/README.md` for details.

# Usage

Show CLI help:

```bash
./src/mfoc-hardnested -h
```
