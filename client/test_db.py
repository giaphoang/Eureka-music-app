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
