from fastapi.testclient import TestClient

from app.main import app


def test_upload_list_and_download() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tracks",
            data={"title": "Demo", "artist": "Candidate", "genre": "Rock"},
            files={"audio": ("demo.mp3", b"ID3" + b"0" * 1024, "audio/mpeg")},
        )
        assert response.status_code == 201
        track = response.json()

        page = client.get("/api/v1/tracks", params={"q": "Candidate"})
        assert page.status_code == 200
        assert page.json()["total"] == 1

        audio = client.get(track["download_url"])
        assert audio.status_code == 200
        assert audio.content.startswith(b"ID3")
