# Design

## Goals

1. Keep the UI event loop free of HTTP, hashing, copying, and database scans.
2. Treat PostgreSQL + server audio volume as the shared source of truth.
3. Treat SQLite + local download folder as durable offline client state.
4. Make every file write crash-safe using `.part` + `fsync` + atomic rename.
5. Handle 8,000 tracks without loading audio bytes or constructing 8,000 widgets at startup.

## Context diagram

```mermaid
flowchart LR
    User[User] --> Client[PySide2 Desktop Client]
    Client -->|REST/JSON + multipart| API[FastAPI Server]
    API --> DB[(PostgreSQL)]
    API --> Audio[(Server Audio Volume)]
    Client --> LocalDB[(SQLite)]
    Client --> Downloads[(Local Download Folder)]
    FMA[FMA Small + Metadata] -->|seed scripts| API
    FMA -->|optional client seed| LocalDB
```

## Container diagram

```mermaid
flowchart TB
    subgraph macOS
        UI[Qt Main Thread]
        Pool[QThreadPool Workers]
        Player[QMediaPlayer]
        Repo[SQLite Repository]
        Files[Downloaded MP3 Files]
    end
    subgraph Docker Compose
        API[FastAPI / Uvicorn]
        PG[(PostgreSQL)]
        Media[(Named Audio Volume)]
    end
    UI --> Pool
    UI --> Player
    UI --> Repo
    Pool --> API
    Pool --> Files
    API --> PG
    API --> Media
    API --> Rec[(Recommendation Artifacts)]
```

## Server ERD

```mermaid
erDiagram
    TRACKS {
        int id PK
        string source_id UK
        string title
        string artist
        string album
        string genre
        string tags
        int duration_ms
        string storage_name UK
        string original_name
        string content_type
        bigint size_bytes
        string checksum_sha256 UK
        datetime created_at
    }
```

## Client ERD

```mermaid
erDiagram
    DOWNLOADED_TRACKS ||--o{ PLAYLIST_ITEMS : referenced_by
    PLAYLISTS ||--o{ PLAYLIST_ITEMS : contains
    DOWNLOADED_TRACKS {
        int server_id PK
        string title
        string artist
        string album
        string genre
        int duration_ms
        string local_path UK
        datetime downloaded_at
    }
    PLAYLISTS {
        int id PK
        string name UK
        datetime created_at
    }
    PLAYLIST_ITEMS {
        int id PK
        int playlist_id FK
        int track_id FK
        int position
    }
```

## Download sequence

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Qt UI Thread
    participant W as Worker Thread
    participant API as FastAPI
    participant FS as Local Files
    participant DB as SQLite

    U->>UI: Click Download
    UI->>W: Submit download task
    W->>API: GET /tracks/{id}/download
    API-->>W: Stream audio bytes
    W->>FS: Write .part + fsync
    W->>FS: Atomic rename
    W-->>UI: Finished(path)
    UI->>DB: Upsert downloaded track
    UI-->>U: Refresh local library
```

## Playback event flow

```mermaid
flowchart LR
    Click[Button click] --> Slot[Qt slot]
    Slot --> Controller[PlaybackController]
    Controller --> Media[QMediaPlayer]
    Media --> Signals[position/state/duration signals]
    Signals --> UI[Update slider, label, button]
```

## Desktop UI shell

The client presentation layer is organized as a reusable PySide2 shell:

```mermaid
flowchart LR
    MainWindow --> Sidebar
    MainWindow --> TopBar
    MainWindow --> Stack[QStackedWidget]
    Stack --> BrowsePage
    Stack --> DownloadsPage
    Stack --> PlaylistPage
    Stack --> UploadPage
    MainWindow --> QueuePanel
    MainWindow --> PlayerBar
```

`MainWindow` remains the orchestration boundary. It owns `MusicAPI`, `ClientDB`, `PlaybackController`, `QThreadPool`, navigation state, selected playlist state, and the current playback queue.

Pages and components own presentation only. They emit Qt signals for user intent and do not perform direct HTTP or SQLite business logic.

Large music collections continue to use `QTableView` with `QAbstractTableModel`. The refactor does not create one widget per track and does not load remote artwork at startup.

## Prompt playlist recommendations

Recommendations are an optional server-side feature. The client sends only a prompt
and requested size. CLAP, FAISS, librosa, and PyTorch are never imported by the
client and are loaded lazily by the server only when recommendation artifacts are
configured. The default backend is the larger LAION music-specialized CLAP
checkpoint on CPU. The Hugging Face `laion/clap-htsat-unfused` backend remains an
optional lightweight fallback.

The recommendation boundary keeps PostgreSQL authoritative. Artifact metadata stores
FMA catalog keys such as `123`, resolved at request time as `Track.source_id =
"fma:123"`. The API returns current server track IDs, not artifact row numbers or
filesystem paths.

```mermaid
flowchart LR
    Prompt[User Prompt] --> Worker[Qt Worker]
    Worker --> API[POST /api/v1/recommendations/playlists]
    API --> CLAP[CPU CLAP Text Embedding]
    CLAP --> FAISS[IndexFlatIP Exact Search]
    FAISS --> MMR[MMR Diversity]
    MMR --> Smooth[Smooth Transition Ordering]
    Smooth --> DB[(PostgreSQL Hydration)]
    DB --> Worker
    Worker --> UI[Recommendation Page]
    UI --> Existing[Existing download, playlist, player flows]
```

Offline artifact build:

```mermaid
flowchart TB
    FMA[FMA Small + tracks.csv] --> Parser[FMA Loader]
    Parser --> Audio[CPU CLAP Audio Embeddings]
    Parser --> Features[RMS Energy + Tempo]
    Audio --> Embeddings[embeddings.npy]
    Features --> Metadata[metadata.jsonl]
    Embeddings --> Index[songs.faiss IndexFlatIP]
    Metadata --> Manifest[manifest.json]
    Index --> Validate[Validate release]
    Manifest --> Validate
    Validate --> Publish[Atomic CURRENT update]
```

Runtime request:

```mermaid
sequenceDiagram
    participant UI as PySide2 UI
    participant W as QThreadPool Task
    participant API as FastAPI
    participant CLAP as Lazy CPU CLAP
    participant IDX as Artifacts + FAISS
    participant DB as PostgreSQL
    UI->>W: prompt, size
    W->>API: POST recommendations/playlists
    API->>CLAP: embed_text(prompt)
    API->>IDX: top K exact cosine search
    API->>IDX: MMR + transition order
    API->>DB: WHERE source_id IN (...)
    DB-->>API: current Track rows
    API-->>W: ordered server track IDs
    W-->>UI: render <= 10 rows
```

Complexity symbols:

- `N`: indexed songs, about 8,000 for FMA Small.
- `D`: CLAP embedding dimension.
- `K`: retrieved candidates, default 50.
- `M`: final playlist size, 5-10.

Exact retrieval is approximately `O(ND)` per prompt. MMR is approximately
`O(K * M * D)` in the straightforward implementation. Greedy transition ordering is
approximately `O(M^2 * D)`. Embedding storage is `O(ND)`. At this scale an
approximate index is unnecessary unless measured evidence shows exact search is too
slow.

MMR uses:

```text
MMR(i) = lambda_mmr * relevance(i)
         - (1 - lambda_mmr) * max_similarity(i, already_selected)
```

Transition ordering uses:

```text
C(a, b) = 0.6 * (1 - cosine(audio_a, audio_b))
        + 0.2 * abs(norm_energy_a - norm_energy_b)
        + 0.2 * abs(norm_tempo_a - norm_tempo_b)
```

Energy and tempo are robust-scaled to `[0, 1]` with neutral imputation for missing
or invalid values. CLAP model loading is process-local, CPU-only, guarded by a
lock, and cached lazily. The artifact manifest records the CLAP backend and model
identifier, and runtime rejects requests when the configured model does not match
the index model because audio and text embeddings must share the same space.
Prompt results use a small bounded LRU cache. Future personalization from user
behavior is intentionally out of scope.

The recommended evaluator setup uses:

```text
Backend: laion
Model: HTSAT-base + music_audioset_epoch_15_esc_90.14.pt
Device: CPU
Audio embedding: offline index command
Text embedding: runtime request
```

This is the heavier infrastructure path: the local checkpoint is about 2.35 GB,
the Docker image needs the optional `laion-clap` stack, and Docker memory must be
large enough to load the model. The benefit is quality: this checkpoint is
music-specialized and gives better prompt relevance for the AI Playlist workflow
than the smaller general-audio Hugging Face model.

The optional Hugging Face setup uses `laion/clap-htsat-unfused`. Its repository is
roughly 618 MB and setup is simpler, but it is a general audio CLAP model; music
recommendation quality for abstract prompts may be weaker. Both backends remain
CPU-only, lazy-loaded server-side, and require rebuilding the FAISS index when
switching models.

Benchmark prompts should include:

- Dreamy electronic music for coding
- Energetic rock for working out
- Calm instrumental music for reading
- Dark experimental music
- Upbeat hip-hop

## API choice

REST is sufficient because the required interactions are request/response operations. JSON is used for catalog metadata; multipart/form-data is used for uploads; `FileResponse` streams downloads. WebSocket or SSE would add lifecycle and reconnection complexity without a real-time requirement.

## Non-functional design

- **No freezing:** network and file transfer work runs in `QThreadPool` tasks.
- **Startup:** SQLite schema creation is constant-size; catalog loading is asynchronous and limited to 500 rows in this starter.
- **Hard-kill persistence:** PostgreSQL named volume, SQLite WAL, atomic file replacement.
- **Memory:** audio is streamed in chunks; rows use a model/view table instead of one widget per track.
- **Stable resources:** each HTTP and SQLite connection uses a context manager.

## Production extensions

- Alembic migrations instead of `create_all`.
- Server-side cursor pagination and genre indexes based on measured queries.
- Cover-art thumbnail cache with bounded LRU.
- Retry/cancel controls in worker tasks.
- Checksums on client downloads.
- Prometheus metrics or structured performance logs.
