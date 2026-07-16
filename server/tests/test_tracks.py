from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import Track
from app.storage import resolve_audio_path


def upload_track(
    client: TestClient,
    *,
    title: str,
    artist: str = "Candidate",
    album: str = "Demo Album",
    genre: str = "Rock",
    tags: str = "tag-a,tag-b",
    audio: bytes | None = None,
    filename: str = "demo.mp3",
) -> dict:
    response = client.post(
        "/api/v1/tracks",
        data={
            "title": title,
            "artist": artist,
            "album": album,
            "genre": genre,
            "tags": tags,
        },
        files={"audio": (filename, audio or (b"ID3" + title.encode() + b"0" * 1024), "audio/mpeg")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_list_and_download() -> None:
    with TestClient(app) as client:
        track = upload_track(client, title="Demo")

        page = client.get("/api/v1/tracks", params={"q": "Candidate"})
        assert page.status_code == 200
        assert page.json()["total"] == 1

        audio = client.get(track["download_url"])
        assert audio.status_code == 200
        assert audio.content.startswith(b"ID3")

        with SessionLocal() as db:
            stored = db.get(Track, track["id"])
            assert stored is not None
            path = resolve_audio_path(stored.storage_name)
        assert path.is_file()
        assert path.stat().st_size > 0


def test_catalog_search_pagination_and_metadata() -> None:
    with TestClient(app) as client:
        first = upload_track(
            client,
            title="Matrix Alpha",
            artist="Artist One",
            album="First Album",
            genre="Electronic",
        )
        second = upload_track(
            client,
            title="Matrix Beta",
            artist="Artist/Slash",
            album="Second Album",
            genre="Electronic",
        )
        third = upload_track(
            client,
            title="Matrix C++ & Jazz?",
            artist="Artist Three",
            album="Odd [Album]",
            genre="Jazz",
        )

        page = client.get("/api/v1/tracks", params={"q": "Matrix", "offset": 1, "limit": 2})
        assert page.status_code == 200
        payload = page.json()
        assert payload["total"] == 3
        assert payload["offset"] == 1
        assert payload["limit"] == 2
        assert [item["id"] for item in payload["items"]] == [second["id"], third["id"]]

        by_title = client.get("/api/v1/tracks", params={"q": "Alpha"}).json()
        assert by_title["total"] == 1
        assert by_title["items"][0]["id"] == first["id"]

        by_artist = client.get("/api/v1/tracks", params={"q": "Artist/Slash"}).json()
        assert by_artist["total"] == 1
        assert by_artist["items"][0]["id"] == second["id"]

        by_album = client.get("/api/v1/tracks", params={"q": "Odd [Album]"}).json()
        assert by_album["total"] == 1
        assert by_album["items"][0]["id"] == third["id"]

        special = client.get("/api/v1/tracks", params={"q": "C++ & Jazz?"}).json()
        assert special["total"] == 1
        assert special["items"][0]["id"] == third["id"]

        empty = client.get("/api/v1/tracks", params={"q": "not-present", "offset": 0, "limit": 5})
        assert empty.status_code == 200
        assert empty.json() == {"items": [], "total": 0, "offset": 0, "limit": 5}


def test_upload_metadata_download_and_duplicate_cleanup() -> None:
    with TestClient(app) as client:
        audio = b"ID3unique-upload" + b"1" * 128
        track = upload_track(
            client,
            title="Uploaded FMA",
            artist="FMA Artist",
            album="FMA Album",
            genre="Hip-Hop",
            tags="fma,small",
            audio=audio,
            filename="uploaded.mp3",
        )
        assert track["title"] == "Uploaded FMA"
        assert track["artist"] == "FMA Artist"
        assert track["album"] == "FMA Album"
        assert track["genre"] == "Hip-Hop"
        assert track["tags"] == "fma,small"

        assert client.get("/api/v1/tracks", params={"q": "Uploaded FMA"}).json()["total"] == 1
        downloaded = client.get(track["download_url"])
        assert downloaded.status_code == 200
        assert downloaded.content == audio

        files_before_duplicate = {path.name for path in settings.audio_root.iterdir()}
        duplicate = client.post(
            "/api/v1/tracks",
            data={"title": "Duplicate", "artist": "FMA Artist"},
            files={"audio": ("duplicate.mp3", audio, "audio/mpeg")},
        )
        assert duplicate.status_code == 409
        assert "already exists" in duplicate.json()["detail"]
        assert {path.name for path in settings.audio_root.iterdir()} == files_before_duplicate


def test_invalid_oversized_upload_and_path_safety(monkeypatch) -> None:
    with TestClient(app) as client:
        unsupported = client.post(
            "/api/v1/tracks",
            data={"title": "Bad", "artist": "Candidate"},
            files={"audio": ("bad.txt", b"not audio", "text/plain")},
        )
        assert unsupported.status_code == 415
        assert unsupported.json()["detail"] == "Unsupported audio format"

        monkeypatch.setattr(settings, "max_upload_bytes", 4)
        oversized = client.post(
            "/api/v1/tracks",
            data={"title": "Too Big", "artist": "Candidate"},
            files={"audio": ("big.mp3", b"ID3" + b"x" * 32, "audio/mpeg")},
        )
        assert oversized.status_code == 413
        assert oversized.json()["detail"] == "File is too large"
        assert list(settings.audio_root.glob("*.part")) == []

        monkeypatch.setattr(settings, "max_upload_bytes", 50 * 1024 * 1024)
        escaped = client.post(
            "/api/v1/tracks",
            data={"title": "Escaped", "artist": "Candidate"},
            files={"audio": ("../../escaped.mp3", b"ID3safe", "audio/mpeg")},
        )
        assert escaped.status_code == 201
        assert escaped.json()["original_name"] == "escaped.mp3"

        with SessionLocal() as db:
            stored = db.get(Track, escaped.json()["id"])
            assert stored is not None
            path = resolve_audio_path(stored.storage_name)
        assert path.is_file()
        assert settings.audio_root.resolve() in path.resolve().parents
