import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from eureka_client.config import DB_PATH, ensure_dirs


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS downloaded_tracks (
    server_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT,
    genre TEXT,
    duration_ms INTEGER,
    local_path TEXT NOT NULL UNIQUE,
    downloaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS playlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    track_id INTEGER NOT NULL REFERENCES downloaded_tracks(server_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    UNIQUE(playlist_id, track_id),
    UNIQUE(playlist_id, position)
);
CREATE INDEX IF NOT EXISTS idx_playlist_items_order ON playlist_items(playlist_id, position);
CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class ClientDB:
    def __init__(self, path: Path = DB_PATH) -> None:
        ensure_dirs()
        self.path = path
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def upsert_download(self, track: dict, local_path: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO downloaded_tracks
                    (server_id, title, artist, album, genre, duration_ms, local_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(server_id) DO UPDATE SET
                    title=excluded.title,
                    artist=excluded.artist,
                    album=excluded.album,
                    genre=excluded.genre,
                    duration_ms=excluded.duration_ms,
                    local_path=excluded.local_path,
                    downloaded_at=CURRENT_TIMESTAMP
                """,
                (
                    track["id"], track["title"], track["artist"], track.get("album"),
                    track.get("genre"), track.get("duration_ms"), local_path,
                ),
            )

    def list_downloads(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM downloaded_tracks ORDER BY downloaded_at DESC, server_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def prune_missing_downloads(self) -> int:
        with self.connect() as conn:
            rows = conn.execute("SELECT server_id, local_path FROM downloaded_tracks").fetchall()
            missing_ids = [
                int(row["server_id"])
                for row in rows
                if not Path(row["local_path"]).is_file()
            ]
            if not missing_ids:
                return 0

            playlist_ids = [
                int(row[0])
                for row in conn.execute(
                    f"""
                    SELECT DISTINCT playlist_id
                    FROM playlist_items
                    WHERE track_id IN ({",".join("?" for _ in missing_ids)})
                    """,
                    missing_ids,
                ).fetchall()
            ]
            conn.executemany(
                "DELETE FROM downloaded_tracks WHERE server_id=?",
                [(track_id,) for track_id in missing_ids],
            )
            for playlist_id in playlist_ids:
                self._normalize_positions(conn, playlist_id)
            return len(missing_ids)

    def create_playlist(self, name: str) -> int:
        with self.connect() as conn:
            cursor = conn.execute("INSERT INTO playlists(name) VALUES (?)", (name.strip(),))
            return int(cursor.lastrowid)

    def list_playlists(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT p.id, p.name, COUNT(pi.id) AS track_count
                FROM playlists p
                LEFT JOIN playlist_items pi ON pi.playlist_id = p.id
                GROUP BY p.id
                ORDER BY p.created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def add_to_playlist(self, playlist_id: int, track_id: int) -> bool:
        with self.connect() as conn:
            position = conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM playlist_items WHERE playlist_id=?",
                (playlist_id,),
            ).fetchone()[0]
            cursor = conn.execute(
                "INSERT OR IGNORE INTO playlist_items(playlist_id, track_id, position) VALUES (?, ?, ?)",
                (playlist_id, track_id, position),
            )
            return cursor.rowcount > 0

    def list_playlist_tracks(self, playlist_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT d.*, pi.position
                FROM playlist_items pi
                JOIN downloaded_tracks d ON d.server_id = pi.track_id
                WHERE pi.playlist_id=?
                ORDER BY pi.position
                """,
                (playlist_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def remove_from_playlist(self, playlist_id: int, track_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM playlist_items WHERE playlist_id=? AND track_id=?",
                (playlist_id, track_id),
            )
            self._normalize_positions(conn, playlist_id)

    def move_playlist_item(self, playlist_id: int, track_id: int, delta: int) -> None:
        with self.connect() as conn:
            current = conn.execute(
                "SELECT position FROM playlist_items WHERE playlist_id=? AND track_id=?",
                (playlist_id, track_id),
            ).fetchone()
            if not current:
                return
            old_position = current[0]
            new_position = old_position + delta
            other = conn.execute(
                "SELECT track_id FROM playlist_items WHERE playlist_id=? AND position=?",
                (playlist_id, new_position),
            ).fetchone()
            if not other:
                return
            conn.execute(
                "UPDATE playlist_items SET position=-1 WHERE playlist_id=? AND track_id=?",
                (playlist_id, track_id),
            )
            conn.execute(
                "UPDATE playlist_items SET position=? WHERE playlist_id=? AND track_id=?",
                (old_position, playlist_id, other[0]),
            )
            conn.execute(
                "UPDATE playlist_items SET position=? WHERE playlist_id=? AND track_id=?",
                (new_position, playlist_id, track_id),
            )

    @staticmethod
    def _normalize_positions(conn: sqlite3.Connection, playlist_id: int) -> None:
        rows = conn.execute(
            "SELECT id FROM playlist_items WHERE playlist_id=? ORDER BY position", (playlist_id,)
        ).fetchall()
        for position, row in enumerate(rows):
            conn.execute("UPDATE playlist_items SET position=? WHERE id=?", (position, row[0]))
