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
