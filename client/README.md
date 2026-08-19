# Desktop client

The client uses a Spotify-inspired PySide2 desktop shell:

- Left navigation sidebar
- Persistent top search bar
- Reusable central pages
- Persistent bottom playback bar
- Optional queue panel
- Dark local theme and bundled SVG icons

The UI refactor evidence is documented under `../docs/ui-refactor/`.

## Exact PyPI wheel compatibility path on macOS

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

## Recommended Ubuntu desktop-client path on Apple Silicon using UTM

Use Ubuntu 22.04 ARM64 in a UTM **Virtualize** VM. Ubuntu provides native ARM64
PySide2 5.15.2 packages, so x86_64 emulation is unnecessary unless you
specifically require the exact PyPI `PySide2==5.15.2.1` wheel. See the root
`README.md` for VM sizing, official Docker installation, FMA sharing, seeding,
and the optional recommendation setup.

### 1. Create the Ubuntu VM

1. Install UTM for macOS:
   - Official UTM installation guide: https://docs.getutm.app/installation/macos/
   - UTM download page: https://mac.getutm.app/
2. Download the Ubuntu 22.04 LTS ARM64 desktop image.
   - https://releases.ubuntu.com/22.04/
3. In UTM, create a new virtual machine:
   - Choose `Virtualize`, not `Emulate`, on Apple Silicon.
   - Choose `Linux`.
   - Architecture: `aarch64`/ARM64.
   - Memory: 8 GB recommended.
   - Disk: 40 GB recommended.
4. Start the VM and install Ubuntu Desktop normally.
5. After installation, shut down the VM, remove/eject the installer ISO, and boot
   into the installed Ubuntu desktop.

UTM also publishes an Ubuntu guide that is useful for general VM creation and
troubleshooting: https://docs.getutm.app/guides/ubuntu/

### 2. Prepare Ubuntu inside the VM

Clone the repository, or copy it into the VM using UTM shared folders:

```bash
git clone <repository-url>
cd Eureka-music-app/client
```

If you use a UTM shared folder, **do not create `.venv` or run Docker in the
SPICE WebDAV/GVFS mount**. Copy the repository to a normal Linux directory:

```bash
cp -a /media/$USER/<shared-folder>/Eureka-music-app ~/Eureka-music-app
cd ~/Eureka-music-app/client
```

### 3. Bootstrap and launch the desktop client

```bash
./scripts/bootstrap_ubuntu_arm64.sh
source .venv/bin/activate
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
