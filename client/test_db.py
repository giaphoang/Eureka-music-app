from pathlib import Path

from eureka_client.db import ClientDB


def test_playlist_order(tmp_path: Path) -> None:
    db = ClientDB(tmp_path / "test.sqlite3")
    for track_id in (1, 2):
        db.upsert_download(
            {
                "id": track_id,
                "title": f"Track {track_id}",
                "artist": "Artist",
                "album": None,
                "genre": None,
                "duration_ms": 30_000,
            },
            str(tmp_path / f"{track_id}.mp3"),
        )
    playlist_id = db.create_playlist("Test")
    db.add_to_playlist(playlist_id, 1)
    db.add_to_playlist(playlist_id, 2)
    db.move_playlist_item(playlist_id, 2, -1)
    assert [row["server_id"] for row in db.list_playlist_tracks(playlist_id)] == [2, 1]


def test_playlist_duplicate_remove_and_restart_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    db = ClientDB(db_path)
    for track_id in (1, 2, 3):
        db.upsert_download(
            {
                "id": track_id,
                "title": f"Track {track_id}",
                "artist": "Artist",
                "album": None,
                "genre": None,
                "duration_ms": 30_000,
            },
            str(tmp_path / f"{track_id}.mp3"),
        )

    playlist_id = db.create_playlist("Manual")
    assert db.add_to_playlist(playlist_id, 1) is True
    assert db.add_to_playlist(playlist_id, 2) is True
    assert db.add_to_playlist(playlist_id, 2) is False
    assert db.add_to_playlist(playlist_id, 3) is True
    assert [row["server_id"] for row in db.list_playlist_tracks(playlist_id)] == [1, 2, 3]

    db.remove_from_playlist(playlist_id, 2)
    assert [
        (row["server_id"], row["position"]) for row in db.list_playlist_tracks(playlist_id)
    ] == [(1, 0), (3, 1)]
    assert [row["server_id"] for row in db.list_downloads()] == [1, 2, 3]

    db.move_playlist_item(playlist_id, 1, 1)
    restarted = ClientDB(db_path)
    assert [row["server_id"] for row in restarted.list_playlist_tracks(playlist_id)] == [3, 1]


def test_empty_and_one_track_playlist(tmp_path: Path) -> None:
    db = ClientDB(tmp_path / "test.sqlite3")
    playlist_id = db.create_playlist("Sparse")
    assert db.list_playlist_tracks(playlist_id) == []

    db.upsert_download(
        {
            "id": 1,
            "title": "Only Track",
            "artist": "Artist",
            "album": None,
            "genre": None,
            "duration_ms": 30_000,
        },
        str(tmp_path / "1.mp3"),
    )
    db.add_to_playlist(playlist_id, 1)
    db.move_playlist_item(playlist_id, 1, -1)
    db.move_playlist_item(playlist_id, 1, 1)
    assert [row["server_id"] for row in db.list_playlist_tracks(playlist_id)] == [1]


def test_playlist_cover_path_persists_after_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    db = ClientDB(db_path)
    playlist_id = db.create_playlist("Covered")
    cover = tmp_path / "cover.png"
    cover.write_bytes(b"image")

    db.set_playlist_cover(playlist_id, str(cover))

    restarted = ClientDB(db_path)
    playlist = restarted.list_playlists()[0]
    assert playlist["cover_path"] == str(cover)


def test_delete_playlist_keeps_downloaded_tracks(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    db = ClientDB(db_path)
    for track_id in (1, 2):
        db.upsert_download(
            {
                "id": track_id,
                "title": f"Track {track_id}",
                "artist": "Artist",
                "album": None,
                "genre": None,
                "duration_ms": 30_000,
            },
            str(tmp_path / f"{track_id}.mp3"),
        )
    playlist_id = db.create_playlist("Delete me")
    db.add_to_playlist(playlist_id, 1)
    db.add_to_playlist(playlist_id, 2)

    db.delete_playlist(playlist_id)

    restarted = ClientDB(db_path)
    assert restarted.list_playlists() == []
    assert [row["server_id"] for row in restarted.list_downloads()] == [1, 2]


def test_prune_missing_downloads_removes_download_and_playlist_reference(tmp_path: Path) -> None:
    db = ClientDB(tmp_path / "test.sqlite3")
    existing = tmp_path / "existing.mp3"
    missing = tmp_path / "missing.mp3"
    existing.write_bytes(b"ID3existing")
    missing.write_bytes(b"ID3missing")
    for track_id, path in ((1, existing), (2, missing)):
        db.upsert_download(
            {
                "id": track_id,
                "title": f"Track {track_id}",
                "artist": "Artist",
                "album": None,
                "genre": None,
                "duration_ms": 30_000,
            },
            str(path),
        )
    playlist_id = db.create_playlist("Cleanup")
    db.add_to_playlist(playlist_id, 1)
    db.add_to_playlist(playlist_id, 2)
    missing.unlink()

    assert db.prune_missing_downloads() == 1

    assert [row["server_id"] for row in db.list_downloads()] == [1]
    playlist_tracks = db.list_playlist_tracks(playlist_id)
    assert [(row["server_id"], row["position"]) for row in playlist_tracks] == [(1, 0)]
