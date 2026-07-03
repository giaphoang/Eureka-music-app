# Eureka Music App - Mac-local starter

A runnable reference implementation for the Eureka Robotics music assignment:

- FastAPI + PostgreSQL server in Docker Compose
- PySide2 desktop client in a Python virtual environment
- Server catalog/search/download/upload
- Local SQLite downloads and playlists
- Play, pause/continue, stop, seek, next/previous, shuffle, loop-one, loop-all
- FMA Small seed scripts for both server and client
- Background workers so HTTP and disk I/O do not block the UI thread

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

## 3. Seed the server with 100 FMA tracks

Expected local data layout:

```text
~/data/fma/
├── fma_small/
│   ├── 000/000002.mp3
│   └── ...
└── fma_metadata/
    └── tracks.csv
```

Run:

```bash
docker compose run --rm \
  -v "$HOME/data/fma:/fma:ro" \
  api python scripts/seed_fma.py /fma --limit 100
```

Verify:

```bash
curl 'http://localhost:8000/api/v1/tracks?limit=3'
```

For final testing, rerun without `--limit`. The script is idempotent and skips existing tracks.

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

## 6. Optional: seed the client directly

This is useful for stress-testing startup and local browsing without downloading 8,000 tracks over HTTP:

```bash
cd client
source .venv/bin/activate
python scripts/seed_fma.py "$HOME/data/fma" --limit 100
python -m eureka_client.app
```

Remove `--limit` for all 8,000 tracks.

## 7. Reset local state

Server database and audio:

```bash
docker compose down -v
```

Client state:

```bash
rm -rf "$HOME/Library/Application Support/EurekaMusic"
```

Or set `EUREKA_DATA_DIR` to a repository-local path during development.

## 8. Recommended five-day build order

- **Day 1:** architecture, Compose, schema, catalog/search, server seed.
- **Day 2:** client shell, SQLite, catalog browsing, background workers, downloads.
- **Day 3:** playback controller, seek/state signals, playlist CRUD and ordering.
- **Day 4:** upload, hard-kill tests, 8,000-track profiling, pagination/model optimization.
- **Day 5:** tests, diagrams, README, Ubuntu verification, demo video, cleanup.

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

## 9. Before submission

This starter intentionally favors clarity. Before submitting, add Alembic migrations, structured logging, API integration tests, Qt model tests, and a CI job that runs server tests and static checks.
