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

## Generated playlists

Open `AI Playlist` from the sidebar, enter a prompt, choose 5-10 songs, and click
`Generate`. The request runs in the existing `QThreadPool` worker path, so the Qt
main thread does not perform HTTP or JSON parsing.

Returned rows are server catalog tracks. `Download all` uses the existing download
method, `Save playlist` stores downloaded generated tracks in the current SQLite
playlist schema, and `Play downloaded` hands local files to the existing player
queue. If the server or recommendation artifacts are unavailable, the page shows a
recoverable error and local playback is unaffected.

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

## Ubuntu desktop-client verification from Apple Silicon using UTM

Use this path when your main computer is an Apple Silicon Mac and you want to
verify the required Ubuntu desktop client in a VM.

### 1. Create the Ubuntu VM

1. Install UTM for macOS:
   - Official UTM installation guide: https://docs.getutm.app/installation/macos/
   - UTM download page: https://mac.getutm.app/
2. Download the Ubuntu 22.04.5 LTS AMD64 desktop ISO:
   - https://releases.ubuntu.com/22.04/
   - Choose `ubuntu-22.04.5-desktop-amd64.iso`.
3. In UTM, create a new virtual machine:
   - Choose `Emulate`, not `Virtualize`, on Apple Silicon.
   - Choose `Linux`.
   - Architecture: `x86_64`.
   - System: `Standard PC (Q35 + ICH9, 2009)` if UTM asks.
   - Memory: at least 4 GB; 8 GB is better if your Mac has enough RAM.
   - CPU cores: at least 2; 4 is better if available.
   - Disk: at least 40 GB.
   - Attach the Ubuntu AMD64 desktop ISO as the boot ISO.
4. Start the VM and install Ubuntu Desktop normally.
5. After installation, shut down the VM, remove/eject the installer ISO, and boot
   into the installed Ubuntu desktop.

Why AMD64 emulation instead of ARM64 virtualization: this client pins
`PySide2==5.15.2.1`, and the assignment target is Ubuntu with PySide2 5.15.x.
Using an AMD64 Ubuntu VM best matches the Python wheel and package ecosystem used
by the documented client setup. ARM64 Ubuntu may be faster in UTM, but dependency
installation for the pinned PySide2 package may fail there.

UTM also publishes an Ubuntu guide that is useful for general VM creation and
troubleshooting: https://docs.getutm.app/guides/ubuntu/

### 2. Prepare Ubuntu inside the VM

Open Terminal in the Ubuntu VM and run:

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv git curl libgl1 \
  libxkbcommon-x11-0 libxcb-xinerama0 \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly gstreamer1.0-libav
```

Clone the repository, or copy it into the VM using UTM shared folders:

```bash
git clone <repository-url>
cd Eureka-music-app/client
```

If you use a UTM shared folder instead of `git clone`, copy the repository to a
normal Linux directory before creating the virtual environment, for example:

```bash
cp -a /media/$USER/<shared-folder>/Eureka-music-app ~/Eureka-music-app
cd ~/Eureka-music-app/client
```

### 3. Install and launch the desktop client

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
export EUREKA_API_URL=http://localhost:8000
python -m eureka_client.app
```

The desktop window should open with the Eureka Music shell. If the backend is not
running yet, catalog/download operations may show recoverable connection errors,
but the client process should still start.

### 4. Optional backend check from the same VM

If you also run the server in the Ubuntu VM, start it from the repository root:

```bash
cd ~/Eureka-music-app
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Then return to `client/`, keep `EUREKA_API_URL=http://localhost:8000`, and launch
the desktop client again.

### 5. Quick verification checklist

Run these from `client/` inside the Ubuntu VM:

```bash
source .venv/bin/activate
python -m pytest
python -m eureka_client.app
```

Manual checks in the desktop window:

- The app opens without crashing.
- The sidebar, search bar, main content area, and bottom player bar are visible.
- If the backend is running, catalog search returns tracks.
- If the backend is not running, the client displays a recoverable connection
  error instead of freezing or crashing.
- Closing the window exits cleanly.
