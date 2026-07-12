# UI Refactor Baseline

Date: 2026-07-16

## Scope

Baseline captured before refactoring the PySide2 desktop client from the current tab-oriented interface to a Spotify-inspired shell.

No UI implementation changes were made before this baseline was recorded.

## Repository

```text
branch=feat/spotify-inspired-ui
commit=5f4900829e60d1cd941f7d3b40acc50c5320c1d4
worktree_before_baseline=clean
```

Branch creation:

```text
git switch -c feat/spotify-inspired-ui
Switched to a new branch 'feat/spotify-inspired-ui'
```

## Test Machine

```text
OS: macOS 26.5 build 25F71
CPU: Apple M3 Pro
shell arch: i386
Python machine: x86_64
Python: 3.10.11
PySide2: 5.15.2
NumPy: 1.26.4
Client execution: x86_64 / Rosetta
```

Target evaluation remains Ubuntu 20.04, 22.04, or 24.04.

## Backend Baseline

Command:

```bash
docker compose up --build -d
```

Result:

```text
api built successfully
db container running and healthy
api container running on 0.0.0.0:8000
```

Health check:

```bash
curl -s http://localhost:8000/health
```

Result:

```json
{"status":"ok"}
```

Catalog count check:

```bash
curl -s 'http://localhost:8000/api/v1/tracks?limit=1'
```

Observed:

```text
total=8003
offset=0
limit=1
first_item_title=Food
first_item_artist=AWOL
```

## Client Data Baseline

An isolated client store was created for baseline measurement:

```text
EUREKA_DATA_DIR=/tmp/eureka-ui-baseline
downloaded_tracks=8000
missing_fma_files=0
```

The first attempt to seed by copying/hardlinking the full FMA Small dataset into `/tmp/eureka-ui-baseline/downloads` failed:

```text
sqlite3.OperationalError: disk I/O error
```

Disk check showed the host data volume was full:

```text
/System/Volumes/Data: 460Gi size, 424Gi used, 163Mi available, 100% capacity
```

For baseline startup and model/view scale measurement, a DB-only isolated store was created with `local_path` values pointing to the read-only FMA source MP3 files under `/Users/zap/Documents/FMA/fma_small`. This avoids modifying or copying the FMA source dataset while preserving an 8,000-row local-library workload.

## Existing Test Results

Client tests:

```bash
cd client
.venv/bin/python -m pytest -q
```

Result:

```text
................                                                         [100%]
16 passed in 0.53s
```

Server tests:

```bash
make server-test
```

Result:

```text
docker compose run --rm api python -m pytest -q
.....                                                                    [100%]
1 warning
5 passed, 1 warning in 0.48s
```

Warning:

```text
StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.
```

## Current UI Architecture

Observed implementation files:

- `client/eureka_client/app.py`
- `client/eureka_client/ui/main_window.py`
- `client/eureka_client/api.py`
- `client/eureka_client/db.py`
- `client/eureka_client/player.py`
- `client/eureka_client/workers/task.py`

Current desktop shell:

- `MainWindow` owns `MusicAPI`, `ClientDB`, `PlaybackController`, and `QThreadPool`.
- Central UI is a `QTabWidget`.
- Tabs are Server catalog, Downloaded, Playlists, and Upload.
- Bottom player controls are embedded below the tab widget but implemented inside `MainWindow`.
- Catalog, downloads, and playlist tracks use `QTableView` with `QAbstractTableModel`.
- Playlist list uses `QListWidget`.
- HTTP search/download/upload operations are submitted through `Task` to `QThreadPool`.
- SQLite local refresh and playlist scans currently run synchronously in `MainWindow`.
- Playback uses one `PlaybackController` and one `QMediaPlayer`.

Current event flow:

```text
button/menu intent -> MainWindow slot -> MusicAPI/ClientDB/PlaybackController
network/file work -> Task on QThreadPool -> Qt signal -> MainWindow UI update
QMediaPlayer signal -> PlaybackController signal -> MainWindow player bar update
```

## Startup Measurements

Method:

- `QT_QPA_PLATFORM=offscreen`
- `EUREKA_DATA_DIR=/tmp/eureka-ui-baseline`
- `EUREKA_API_URL=http://localhost:8000`
- Constructed the real `QApplication` and `MainWindow`.
- Startup complete when:
  - main window was visible;
  - a zero-delay `QTimer` had fired, proving event-loop responsiveness;
  - local table had 8,000 rows;
  - catalog table had first page loaded.

Results:

```text
run=1 elapsed=0.590127 visible=True responsive=True local_rows=8000 catalog_rows=500 rss_mb=100.3
run=2 elapsed=0.198235 visible=True responsive=True local_rows=8000 catalog_rows=500 rss_mb=101.6
run=3 elapsed=0.212392 visible=True responsive=True local_rows=8000 catalog_rows=500 rss_mb=102.0
run=4 elapsed=0.194357 visible=True responsive=True local_rows=8000 catalog_rows=500 rss_mb=101.6
run=5 elapsed=0.194776 visible=True responsive=True local_rows=8000 catalog_rows=500 rss_mb=100.9
```

Summary:

```text
startup_min=0.194357
startup_median=0.198235
startup_max=0.590127
target_under_10s=VERIFIED_PASS
```

## Memory Measurements

Measured with:

```bash
ps -o rss= -p <pid>
```

RSS during startup baseline:

```text
rss_min_mb=100.3
rss_median_mb=101.6
rss_max_mb=102.0
```

Status:

```text
idle_startup_rss=VERIFIED_PASS
15_to_40_minute_plateau=NOT_VERIFIED in this baseline run
```

The long plateau harness exists at `client/scripts/memory_plateau.py`, but the required 15-40 minute run was not executed during this baseline step.

## Screenshot

Baseline screenshot:

```text
docs/ui-refactor/screenshots/baseline-current-ui.png
```

Capture result:

```text
local_rows=8000
catalog_rows=500
image_size=122K
```

## Functional Checklist

Legend:

- `VERIFIED_PASS`: executed during this baseline session.
- `OBSERVED`: covered by inspected tests or existing implementation.
- `NOT_VERIFIED`: not rerun manually in this headless baseline session.

### Server Catalog

```text
List tracks: VERIFIED_PASS via live API count and server tests.
Paginate tracks: VERIFIED_PASS via server tests.
Search by title: VERIFIED_PASS via server tests.
Search by artist: VERIFIED_PASS via server tests.
Search by album: VERIFIED_PASS via server tests.
Handle empty search results: VERIFIED_PASS via server tests.
Handle special characters: VERIFIED_PASS via server tests.
Return total/offset/limit: VERIFIED_PASS via server tests and live API count.
```

### Download

```text
Download valid track: VERIFIED_PASS via client tests.
Downloaded file exists: VERIFIED_PASS via client tests.
Downloaded file non-zero: VERIFIED_PASS via client tests.
Interrupted download not completed: VERIFIED_PASS via client tests.
.part cleanup on ordinary failure: VERIFIED_PASS via client tests.
Duplicate download behavior: VERIFIED_PASS via client tests.
Audible local playback after download: NOT_VERIFIED in this headless baseline session.
```

### Upload

```text
Upload valid MP3 metadata/download behavior: VERIFIED_PASS via server tests.
Duplicate upload clear 409 notification path: VERIFIED_PASS via client and server tests.
Invalid upload clear error: VERIFIED_PASS via server tests.
Oversized upload clear error: VERIFIED_PASS via server tests.
Failed duplicate insert does not leave orphan final file: VERIFIED_PASS via server tests.
Filename path traversal cannot escape audio directory: VERIFIED_PASS via server tests.
Live GUI upload workflow: NOT_VERIFIED in this headless baseline session.
```

### Local Playback

```text
Queue selected downloaded track: VERIFIED_PASS via player tests.
Previous/next/manual order: VERIFIED_PASS via player tests.
Shuffle order construction: VERIFIED_PASS via player tests.
Loop all next/previous behavior: VERIFIED_PASS via player tests.
Missing selected local file does not play another track: VERIFIED_PASS via player tests.
Playback shutdown cleanup: VERIFIED_PASS via player tests.
Audible play/pause/continue/stop/seek: NOT_VERIFIED in this headless baseline session.
```

### Playlists

```text
Create playlist: VERIFIED_PASS via client DB tests.
Add downloaded tracks: VERIFIED_PASS via client DB tests.
Duplicate addition handled without duplicate row: VERIFIED_PASS via client DB tests.
Remove track: VERIFIED_PASS via client DB tests.
Move up/down: VERIFIED_PASS via client DB tests.
Manual order after restart: VERIFIED_PASS via client DB tests.
Empty playlist: VERIFIED_PASS via client DB tests.
One-track playlist: VERIFIED_PASS via client DB tests.
Playlist playback audible/manual loop modes: NOT_VERIFIED in this headless baseline session.
```

### User Experience

```text
Main window launch with 8,000 local rows and 500 catalog rows: VERIFIED_PASS.
Current UI remains tab-based and utilitarian: OBSERVED.
Non-blocking HTTP download/search/upload wiring through QThreadPool: OBSERVED in code.
Live resize, keyboard, and audio responsiveness: NOT_VERIFIED in this headless baseline session.
```

## Known Issues Before Refactor

1. Current UI is tab-oriented and not Spotify-inspired.
2. Player bar is implemented directly in `MainWindow`, not as a reusable component.
3. There is no sidebar, top navigation/search shell, or optional queue panel.
4. Loading, empty, success, and error states are inconsistent and mostly modal/status-bar based.
5. SQLite local refresh and playlist scans are synchronous in `MainWindow`; current measured cost is acceptable, but this is a risk area for slower machines.
6. Full FMA copy/hardlink seed into `/tmp` failed because the host disk was full. Baseline scale measurement used a DB-only store pointing to read-only FMA files.
7. Native macOS/Rosetta `QMediaPlayer` crash soak remains a separate NOT_VERIFIED item from prior validation.
8. 15-40 minute memory plateau validation was not rerun during this baseline.

## Baseline Status

```text
automated_tests=VERIFIED_PASS
backend_running=VERIFIED_PASS
client_startup_8000_rows=VERIFIED_PASS
baseline_screenshot=VERIFIED_PASS
manual_gui_audio_regression=NOT_VERIFIED
long_memory_plateau=NOT_VERIFIED
```
