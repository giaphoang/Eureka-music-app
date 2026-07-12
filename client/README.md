# Desktop client

The client uses a Spotify-inspired PySide2 desktop shell:

- Left navigation sidebar
- Persistent top search bar
- Reusable central pages
- Persistent bottom playback bar
- Optional queue panel
- Dark local theme and bundled SVG icons

The UI refactor evidence is documented under `../docs/ui-refactor/`.

## Important for Apple Silicon Macs

PySide2 5.15.2.1 on macOS supports Intel x86_64, not Apple Silicon arm64/aarch64. On an Apple Silicon Mac, Python normally runs as arm64, but the available PySide2 macOS wheel was compiled for x86_64. Because those architectures do not match, pip reports that no compatible version exists.

Run an Intel shell through Rosetta first, then create the virtual environment inside that shell. The server may continue running natively in Docker Desktop.

Install the official Python 3.10.11 **macOS universal2** package. Its default binary is:

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10
```

Then verify the Intel side of the universal binary:


```bash
PY310=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10
arch -x86_64 "$PY310" -c 'import platform; print(platform.machine())'
# Expected: x86_64
```

Create and run the client environment:

```bash
arch -x86_64 zsh
cd client
./scripts/bootstrap_macos.sh
./scripts/run_macos.sh
```

For an Intel Mac, the same scripts create a normal native environment. To use a different Python 3.10 binary:

```bash
PYTHON_BIN=/path/to/python3.10 ./scripts/bootstrap_macos.sh
```

Optional settings:

```bash
export EUREKA_API_URL=http://localhost:8000
export EUREKA_DATA_DIR="$PWD/.local-data"
```

## Seed the local store

```bash
python scripts/seed_fma.py "$HOME/data/fma" --limit 100
```

Remove `--limit 100` to seed all 8,000 tracks.

## Memory plateau validation

The long memory test repeats local refreshes, playlist refreshes, catalog searches, and muted playback queue loads while sampling RSS with `ps`.

Run it against a seeded client store for 15-40 minutes:

```bash
export EUREKA_DATA_DIR="$PWD/.local-data"
export EUREKA_API_URL=http://localhost:8000
python scripts/memory_plateau.py \
  --duration-minutes 30 \
  --sample-seconds 10 \
  --csv "$PWD/.local-data/memory-plateau.csv"
```

Use `--visible` to show the real window during the run. By default the harness uses Qt offscreen mode.

The result is acceptable when the summary reports `plateau_status=PASS`, meaning the tail of the run stayed within the configured growth and slope limits.

## Ubuntu 22.04 verification

```bash
sudo apt update
sudo apt install -y python3.10-venv libgl1 libxkbcommon-x11-0 libxcb-xinerama0 \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly gstreamer1.0-libav
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m eureka_client.app
```
