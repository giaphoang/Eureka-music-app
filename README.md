# Eureka Music App 

An Implementation for the Eureka Robotics music app on Ubuntu:

- FastAPI + PostgreSQL server in Docker Compose
- PySide2 desktop client in a Python virtual environment
- Spotify-inspired desktop client shell with sidebar navigation, top search, persistent player bar, and optional queue panel
- Server catalog/search/download/upload
- Local SQLite downloads and playlists
- Play, pause/continue, stop, seek, next/previous, shuffle, loop-one, loop-all
- FMA Small seed scripts for both server and client
- Background workers so HTTP and disk I/O do not block the UI thread
- Optional CPU-only CLAP prompt-to-playlist retrieval on the server with the
  music-specialized LAION CLAP checkpoint by default, exact FAISS search, MMR
  diversity, and smooth transition ordering

## 1. Mac architecture decision

### Intel Mac

Run Docker Desktop and Python 3.10 normally.

### Apple Silicon Mac

Run Docker Desktop normally (ARM native), but run the desktop client using an x86_64 Python 3.10 process under Rosetta because the required PySide2 wheel is Intel-only.

Install Rosetta once:

```bash
softwareupdate --install-rosetta --agree-to-license
```

Install the official Python 3.10.11 **macOS universal2** package. Its default binary is:

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10
```

Then verify the Intel side of the universal binary:


```bash
PY310=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10
arch -x86_64 "$PY310" -c 'import platform; print(platform.machine())'
# x86_64
```

Do not use Python 3.11+ for this assignment.

## 2. Start the backend

```bash
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

API documentation: `http://localhost:8000/docs`

Export the same OpenAPI contract to a reviewable JSON file:

```bash
make api-docs
```

Team development checks:

```bash
python -m pip install -r requirements-dev.txt
make lint
make type-check
make test
```

`make lint` runs Ruff against `client/` and `server/`. `make type-check` runs
mypy in gradual mode using the root `pyproject.toml`. `make test` runs the
client tests locally and the server tests through Docker Compose.

Recommendations are optional. Model caches, generated embeddings, and FAISS
artifacts are kept outside Git. The default recommendation backend uses the
larger music-specialized LAION CLAP checkpoint for better playlist quality. The
smaller Hugging Face `laion/clap-htsat-unfused` backend remains available as a
lighter infrastructure option with weaker music-specific prompt quality. Exact
retrieval is appropriate here because FMA Small is about 8,000 tracks: scanning
`N` normalized vectors is simple and small enough to avoid approximate-index
complexity.

## UI refactor evidence

The desktop client now uses a Spotify-inspired PySide2 shell while preserving the existing server, SQLite, download, upload, playback, playlist, worker, and seed behavior.

Refactor documentation:

- `docs/ui-refactor/BASELINE.md`
- `docs/ui-refactor/UI_DESIGN.md`
- `docs/ui-refactor/COMPONENT_MAP.md`
- `docs/ui-refactor/REGRESSION_REPORT.md`
- `docs/ui-refactor/PERFORMANCE_COMPARISON.md`
- `docs/ui-refactor/MANUAL_TEST_RESULTS.md`
- `docs/ui-refactor/SCREENSHOTS.md`

## 3. Install FMA Small and seed data

Download the dataset from the official FMA project: `https://github.com/mdeff/fma`.
Only two archives are required for this starter:

- `fma_metadata.zip`, which contains `fma_metadata/tracks.csv`
- `fma_small.zip`, which contains the MP3 files

The FMA folder can live next to this repository or anywhere else on your machine. The examples below use `$HOME/Documents/FMA`; if you choose another location, replace that path in each command.

Create the dataset directory:

```bash
mkdir -p "$HOME/Documents/FMA"
cd "$HOME/Documents/FMA"
pwd
```

Expected:

```text
/Users/<your-username>/Documents/FMA
```

Download the metadata:

```bash
curl -L \
  --fail \
  --retry 5 \
  --continue-at - \
  -o fma_metadata.zip \
  https://os.unil.cloud.switch.ch/fma/fma_metadata.zip
```

Download FMA Small:

```bash
curl -L \
  --fail \
  --retry 5 \
  --continue-at - \
  -o fma_small.zip \
  https://os.unil.cloud.switch.ch/fma/fma_small.zip
```

Verify the downloads on macOS:

```bash
cd "$HOME/Documents/FMA"

echo "f0df49ffe5f2a6008d7dc83c6915b31835dfe733  fma_metadata.zip" \
  | shasum -a 1 -c -

echo "ade154f733639d52e35e32f5593efe5be76c6d70  fma_small.zip" \
  | shasum -a 1 -c -
```

Expected:

```text
fma_metadata.zip: OK
fma_small.zip: OK
```

Unzip both archives:

```bash
cd "$HOME/Documents/FMA"
unzip fma_metadata.zip
unzip fma_small.zip
```

Expected file structure:

```text
~/Documents/
├── FMA/
│   ├── fma_small/
│   │   ├── 000/
│   │   ├── 001/
│   │   └── ...
│   └── fma_metadata/
│       └── tracks.csv
│
└── eureka-music-starter/
    ├── compose.yaml
    ├── server/
    │   └── scripts/
    │       └── seed_fma.py
    └── client/
        └── scripts/
            └── seed_fma.py
```

The path supplied to both seed scripts is the FMA parent directory, for example `$HOME/Documents/FMA`. Do not pass `fma_small/` or `fma_metadata/` directly.

### Seed the server store

The server seed script runs inside Docker, so it cannot directly access `/Users/<your-username>/Documents/FMA`. Mount the Mac folder into the container, then pass the mounted container path as the script CLI argument.

From the repository root:

```bash
cd "$HOME/Documents/eureka-music-starter"
```

Verify the Docker mount first:

```bash
docker compose run --rm \
  -v "$HOME/Documents/FMA:/dataset/fma:ro" \
  api sh -lc '
    echo "CLI root would be: /dataset/fma"
    test -d /dataset/fma/fma_small &&
    echo "Found fma_small"

    test -f /dataset/fma/fma_metadata/tracks.csv &&
    echo "Found tracks.csv"

    find /dataset/fma/fma_small -type f -name "*.mp3" | head
  '
```

Expected:

```text
Found fma_small
Found tracks.csv
/dataset/fma/fma_small/000/000002.mp3
...
```

Then seed 100 tracks:

```bash
docker compose run --rm \
  -v "$HOME/Documents/FMA:/dataset/fma:ro" \
  api python -m scripts.seed_fma /dataset/fma --limit 100
```

The important part is `python -m scripts.seed_fma /dataset/fma --limit 100`. `/dataset/fma` is the CLI argument received by the server script inside Docker, and the volume mapping only makes the Mac folder available there:

```text
Mac:       $HOME/Documents/FMA
Container: /dataset/fma
```

Inside Docker, the script resolves:

```text
/dataset/fma/fma_small
/dataset/fma/fma_metadata/tracks.csv
```

Verify the seeded server catalog:

```bash
curl 'http://localhost:8000/api/v1/tracks?limit=3'
```

For final testing, rerun the seed command without `--limit`. The server script is idempotent and skips existing tracks.

### Seed the client store

The client seed script runs directly on macOS, so pass the Mac filesystem path:

```bash
cd "$HOME/Documents/eureka-music-starter/client"
source .venv/bin/activate
python scripts/seed_fma.py "$HOME/Documents/FMA" --limit 100
```

For final testing, rerun without `--limit`.

Both scripts receive the same logical FMA parent directory, but expressed in the filesystem of the environment where each script runs:

```text
Server Docker CLI argument: /dataset/fma
Client macOS CLI argument:  /Users/<your-username>/Documents/FMA
```

## 4. Start the desktop client

### Apple Silicon

PySide2 5.15.2.1 requires the desktop client to run in an Intel x86_64/Rosetta shell. See `client/README.md` for the full Apple Silicon setup notes.

```bash
arch -x86_64 zsh
cd client
./scripts/bootstrap_macos.sh
./scripts/run_macos.sh
```

### Intel Mac

```bash
cd client
./scripts/bootstrap_macos.sh
./scripts/run_macos.sh
```

## 5. End-to-end verification

1. Open **Server catalog** and search.
2. Select a row and download it.
3. Open **Downloaded** and play the track.
4. Test pause/continue, stop, seeking, next/previous, shuffle, and loop.
5. Create a playlist, add tracks, reorder them, and play the playlist.
6. Open **Upload**, choose an FMA MP3, enter title/artist, and upload it.
7. Restart the client and confirm downloads and playlists remain.
8. Run `docker compose down`, then `docker compose up -d`, and confirm the server catalog remains.

## 6. Reset local state

Server database and audio:

```bash
docker compose down -v
```

Client state:

```bash
rm -rf "$HOME/Library/Application Support/EurekaMusic"
```

Or set `EUREKA_DATA_DIR` to a repository-local path during development.


## Final Ubuntu target

Use **Ubuntu 22.04 x86_64** for the final verification. It includes Python 3.10, which matches the required PySide2 package.

```bash
sudo apt update
sudo apt install -y python3.10-venv libgl1 libxkbcommon-x11-0 libxcb-xinerama0 \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly gstreamer1.0-libav
cd client
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m eureka_client.app
```

Run the complete 8,000-track test on Ubuntu before recording the submission video.

## 8. Before submission

This starter intentionally favors clarity. Before submitting, add Alembic migrations, structured logging, API integration tests, Qt model tests, and a CI job that runs server tests and static checks.
