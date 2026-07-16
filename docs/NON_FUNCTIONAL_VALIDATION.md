# Non-Functional Validation

Date: 2026-07-16

## Test machine

Observed on macOS:

```text
Model Identifier: Mac15,6
CPU cores: 11 (5 performance, 6 efficiency)
Memory: 18 GB
macOS: 26.5 build 25F71
Shell/Python architecture for client: x86_64 / Rosetta
Python: 3.10.11
PySide2: 5.15.2.1
FMA Small MP3 files: 8000
FMA metadata small subset rows: 8000
FMA audio size: 7.4G
```

Docker was available for server checks. The API and PostgreSQL containers were constrained by Docker Desktop to about 1.925 GiB visible memory.

## Fixes made during validation

The documented seed-script invocation failed before scale tests:

```text
ModuleNotFoundError: No module named 'eureka_client'
```

Root cause: running `python scripts/seed_fma.py` places `scripts/` on `sys.path`, not the project root.

Fix: both seed scripts now insert their project root into `sys.path` before importing application modules:

- `client/scripts/seed_fma.py`
- `server/scripts/seed_fma.py`

## 1. Startup time under 10 seconds

### Method

Startup completion was measured with an offscreen Qt harness that:

1. sets `EUREKA_DATA_DIR` to an isolated seeded client store;
2. creates `QApplication`;
3. instantiates and shows the real `MainWindow`;
4. processes Qt events;
5. waits until:
   - `window.isVisible()` is true;
   - a zero-delay `QTimer` fires, proving event-loop responsiveness;
   - the local table has the expected row count;
   - for real-backend runs, the first catalog page has rows.

Because forcibly dropping macOS disk cache is not safe here, "cold" means the first launch in the measurement series after seeding. "Warm" means subsequent launches.

### 100 local tracks, real backend

```text
run=1 elapsed=0.114890s local_rows=100 catalog_rows=500 visible=True responsive=True maxrss=93749248
run=2 elapsed=0.111772s local_rows=100 catalog_rows=500 visible=True responsive=True maxrss=93523968
run=3 elapsed=0.114218s local_rows=100 catalog_rows=500 visible=True responsive=True maxrss=93859840
```

Summary:

```text
cold-ish: 0.114890s
warm min: 0.111772s
warm median: 0.112995s
warm max: 0.114218s
target: PASS, under 10s
```

### 8,000 local tracks, real backend

```text
run=1 elapsed=0.831468s local_rows=8000 catalog_rows=500 visible=True responsive=True maxrss=105267200
run=2 elapsed=0.125272s local_rows=8000 catalog_rows=500 visible=True responsive=True maxrss=104792064
run=3 elapsed=0.119829s local_rows=8000 catalog_rows=500 visible=True responsive=True maxrss=104734720
run=4 elapsed=0.130189s local_rows=8000 catalog_rows=500 visible=True responsive=True maxrss=105480192
run=5 elapsed=0.129381s local_rows=8000 catalog_rows=500 visible=True responsive=True maxrss=104951808
```

Summary:

```text
cold-ish: 0.831468s
all-run min: 0.119829s
all-run median: 0.129381s
all-run max: 0.831468s
warm min: 0.119829s
warm median: 0.127327s
warm max: 0.130189s
target: PASS, under 10s
```

### 8,000 local tracks, local-only/stubbed catalog

This isolates local-library startup from backend timing:

```text
run=1 elapsed=0.200165s rows=8000 visible=True responsive=True maxrss=97959936
run=2 elapsed=0.093382s rows=8000 visible=True responsive=True maxrss=99315712
run=3 elapsed=0.085680s rows=8000 visible=True responsive=True maxrss=98541568
run=4 elapsed=0.084524s rows=8000 visible=True responsive=True maxrss=98603008
run=5 elapsed=0.084300s rows=8000 visible=True responsive=True maxrss=98902016
run=6 elapsed=0.087876s rows=8000 visible=True responsive=True maxrss=98213888
```

Result: PASS.

## 2. UI must never freeze or hang

### Blocking-operation inspection

Observed implementation:

```text
HTTP catalog search: QThreadPool Task
HTTP download: QThreadPool Task in UI workflow
HTTP upload: QThreadPool Task in UI workflow
Search result rendering: UI thread, up to 500 rows/page
SQLite local download scan: UI thread
SQLite playlist scan: UI thread
FMA server seed: CLI script, outside Qt UI
FMA client seed: CLI script, outside Qt UI
Server file hashing/copying: CLI/API server, outside Qt UI
Client direct file download writes: worker in UI workflow
Playlist loading: UI thread
Large local table rendering: QTableView model, not 8,000 row widgets
```

### Instrumented responsiveness

A Qt timer heartbeat and operation timing were run against the 8,000-track local store:

```text
startup_ready=True local_rows=8000 catalog_rows=500 rss_start_mb=98.4
download_median_ms=14.258 download_max_ms=47.507 count=5
local_refresh_median_ms=19.308 local_refresh_max_ms=33.971 count=200
playlist_refresh_median_ms=0.558 playlist_refresh_max_ms=1.086 count=500
search_median_ms=23.317 search_max_ms=38.197 count=100
queue_load_median_ms=54.907 queue_load_max_ms=75.553 count=50
heartbeat_count=212 heartbeat_max_gap_ms=227.555
```

Interpretation:

- The measured synchronous UI-thread operations stayed below 100 ms individually in this harness.
- The heartbeat gap exceeded the 100-200 ms warning band once. The harness included direct synchronous downloads for memory measurement; the actual UI workflow runs downloads in a worker, so this exact gap is not a proven app freeze.
- Live manual tests while audio is playing remain NOT_VERIFIED.

Required manual checks:

1. Search while audio is playing.
2. Download while audio is playing.
3. Upload while audio is playing.
4. Switch tabs during a download.
5. Move and resize the window during network activity.
6. Stop the backend and attempt searches/downloads.
7. Restore the backend and recover without restarting the client.

Current status: PARTIAL PASS by instrumentation and code inspection; live GUI/audio responsiveness remains NOT_VERIFIED.

## 3. Stable memory usage

### Client memory

Measured with `ps -o rss= -p <pid>` inside the validation process.

```text
rss_samples_mb=
  after_startup_idle:98.1
  after_5_direct_downloads:105.1
  after_200_local_refreshes:126.3
  after_500_playlist_refreshes:126.2
  after_100_searches:132.3
  after_50_queue_loads:146.0
  after_1s_idle:145.8

rss_initial_mb=98.1
rss_peak_mb=146.0
rss_final_mb=145.8
growth_mb=47.7
```

Interpretation:

- Memory increased during repeated operations and did not return to initial RSS after 1 second idle.
- No unbounded leak was proven by this short deterministic run.
- The largest increase appeared after QMediaPlayer/QMediaContent queue loading and repeated table refresh/search activity, consistent with lazy Qt/media caches or retained Python/Qt allocations.

Potential leak areas inspected:

```text
QMediaPlayer objects: one PlaybackController owns one QMediaPlayer.
Repeated Qt signal connections: no repeated signal connections observed in repeated operations.
QMediaContent objects: replaced through setMedia during queue loads.
QThreadPool tasks: task objects are not retained by MainWindow after completion.
HTTP clients: context managers close clients.
Table models: replace_tracks swaps the list reference.
SQLite connections: context managers close connections.
Temporary files: download failure removes .part; SIGKILL can leave .part.
```

Status: PARTIAL PASS. Stable plateau over 15-30 minutes is NOT_VERIFIED.

### Server memory

Idle before repeated operations:

```text
api mem=44.76MiB / 1.925GiB
db  mem=37.55MiB / 1.925GiB
```

After 100 catalog searches, 10 downloads, and one unique MP3 upload:

```text
api mem=47.04MiB / 1.925GiB
db  mem=37.67MiB / 1.925GiB
```

After hard-kill restart:

```text
api mem=64.28MiB / 1.925GiB
db  mem=29.77MiB / 1.925GiB
```

Status: PASS for short deterministic operation set. Long 15-30 minute plateau remains NOT_VERIFIED.

## 4. Hard-kill and persistence reliability

### Client

Isolated client data dir: `/tmp/eureka-nfr-kill-client`.

Procedure:

1. Create completed local download rows.
2. Create a playlist.
3. Reorder playlist items.
4. Start a child process writing `incomplete.mp3.part`.
5. Kill the child with SIGKILL.
6. Reopen SQLite.

Observed:

```text
child_exit -9
downloads [(1, '1.mp3'), (2, '2.mp3')]
playlist_order [2, 1]
integrity ok
part_exists True
incomplete_completed False
```

Status:

- Completed downloads remain: PASS.
- Incomplete downloads are not treated as complete: PASS.
- Playlists remain: PASS.
- Manual order remains: PASS.
- SQLite integrity check: PASS.
- Incomplete `.part` cleanup: RISK. The `.part` file remains after SIGKILL. It is not treated as complete, but startup cleanup/recovery is not implemented.

### Server

Procedure:

1. Full seed server catalog.
2. Upload a unique MP3-like file derived from FMA audio.
3. `docker kill` API and DB containers.
4. `docker compose up -d`.
5. Verify count and uploaded audio download.

Observed:

```text
docker kill eureka-music-starter-api-1 eureka-music-starter-db-1
docker compose up -d
total 8001
download_http=200 size=959552
uploaded_download_nonzero=yes
```

Status: PASS. Metadata and audio survived abrupt API/DB container kill and restart without removing volumes.

## 5. Full 8,000-track scale

### Dataset

```text
FMA Small MP3 files: 8000
FMA metadata small subset rows: 8000
Missing during server seed: 0
```

### Client full seed

First full seed:

```text
Seeded 8000 downloaded tracks into /tmp/eureka-nfr-8000/client.sqlite3
real 49.11
user 4.87
sys 12.15
```

Rerun:

```text
Seeded 8000 downloaded tracks into /tmp/eureka-nfr-8000/client.sqlite3
real 28.03
user 5.15
sys 7.86
downloads 8000
```

Status: PASS for final count and no duplicate rows. The script reruns all upserts rather than reporting skipped rows.

### Server full seed

Full seed into existing 100-track server:

```text
Done: inserted=7900, skipped=100, missing=0
real 83.15
```

Idempotency rerun:

```text
Done: inserted=0, skipped=8000, missing=0
real 5.31
```

Catalog count after full seed:

```text
total 8000
```

After one unique upload for server memory/persistence testing:

```text
total 8001
```

Status: PASS.

### Scale behavior

```text
Startup with 8000 local tracks and real backend: max 0.831468s
Catalog first page size: 500
Local table rows: 8000
100 search operations: median 23.317 ms, max 38.197 ms in harness
200 local refreshes: median 19.308 ms, max 33.971 ms
500 playlist refreshes: median 0.558 ms, max 1.086 ms
50 queue loads: median 54.907 ms, max 75.553 ms
```

The UI uses `QTableView` with `QAbstractTableModel`, not 8,000 heavyweight row widgets.

Status: PASS for measured startup, count, pagination, search responsiveness, and model/view rendering. Live manual UI/audio scale remains NOT_VERIFIED.

## Remaining risks and recommended fixes

1. Add client startup cleanup for stale `*.part` files, or document that stale partial files are safely ignored.
2. Add a longer 15-30 minute memory plateau test, preferably with `psutil` or a repeatable external sampler.
3. Add pytest-qt or a small dedicated GUI harness that measures heartbeat gaps while using the real UI workflows for search/download/upload rather than direct API calls.
4. Add manual or automated audio-backend verification for playback, seek, pause/continue, loop one, loop all, and visible playback errors.
5. Consider moving `refresh_local()` and playlist DB scans into workers if future measurements exceed the 100-200 ms responsiveness band on slower machines or larger local stores.
