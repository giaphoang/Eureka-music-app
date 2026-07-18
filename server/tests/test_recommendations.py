from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.schemas import RecommendationPlaylistOut, RecommendationTrackOut


def test_recommendation_status_does_not_load_model(monkeypatch) -> None:
    from pathlib import Path

    monkeypatch.setattr(settings, "recommendation_enabled", True)
    monkeypatch.setattr(settings, "clap_backend", "laion")
    monkeypatch.setattr(settings, "clap_audio_model", "HTSAT-base")
    monkeypatch.setattr(settings, "clap_checkpoint", Path("/models/music_audioset_epoch_15_esc_90.14.pt"))

    with TestClient(app) as client:
        response = client.get("/api/v1/recommendations/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["device"] == "cpu"
    assert payload["model_backend"] == "laion"
    assert payload["model_id"] == "HTSAT-base:music_audioset_epoch_15_esc_90.14.pt"
    assert payload["model_loaded"] is False
    assert payload["checkpoint_configured"] is True


def test_hf_backend_status_does_not_require_checkpoint(monkeypatch) -> None:
    monkeypatch.setattr(settings, "recommendation_enabled", True)
    monkeypatch.setattr(settings, "clap_backend", "hf")
    monkeypatch.setattr(settings, "hf_clap_model_id", "laion/clap-htsat-unfused")
    monkeypatch.setattr(settings, "clap_checkpoint", None)

    with TestClient(app) as client:
        response = client.get("/api/v1/recommendations/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_backend"] == "hf"
    assert payload["model_id"] == "laion/clap-htsat-unfused"
    assert payload["checkpoint_configured"] is True


def test_laion_backend_status_requires_checkpoint(monkeypatch) -> None:
    monkeypatch.setattr(settings, "recommendation_enabled", True)
    monkeypatch.setattr(settings, "clap_backend", "laion")
    monkeypatch.setattr(settings, "clap_checkpoint", None)

    with TestClient(app) as client:
        response = client.get("/api/v1/recommendations/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_backend"] == "laion"
    assert payload["checkpoint_configured"] is False


def test_model_signature_prevents_mixing_models() -> None:
    from pathlib import Path

    from app.recommendation.embedding_backends import model_signature

    assert model_signature("hf", None, "HTSAT-base", "laion/clap-htsat-unfused") == (
        "hf",
        "laion/clap-htsat-unfused",
    )
    assert model_signature("laion", Path("/models/music.pt"), "HTSAT-base", "ignored") == (
        "laion",
        "HTSAT-base:music.pt",
    )


def test_recommendation_request_validation() -> None:
    with TestClient(app) as client:
        short_prompt = client.post("/api/v1/recommendations/playlists", json={"prompt": "  x  ", "size": 10})
        bad_size = client.post("/api/v1/recommendations/playlists", json={"prompt": "valid prompt", "size": 4})

    assert short_prompt.status_code == 422
    assert bad_size.status_code == 422


def test_recommendation_playlist_uses_service_response(monkeypatch) -> None:
    from app.routers import recommendations

    def fake_hydrate(_db, prompt: str, size: int) -> RecommendationPlaylistOut:
        assert prompt == "dreamy electronic focus"
        assert size == 5
        return RecommendationPlaylistOut(
            prompt=prompt,
            strategy="fake",
            tracks=[
                RecommendationTrackOut(
                    position=1,
                    track_id=123,
                    title="Song",
                    artist="Artist",
                    album=None,
                    genre="Electronic",
                    download_url="/api/v1/tracks/123/download",
                    original_name="song.mp3",
                    duration_ms=30_000,
                    prompt_similarity=0.9,
                    mmr_score=0.8,
                    transition_cost_from_previous=None,
                )
            ],
        )

    monkeypatch.setattr(recommendations, "hydrate_recommendations", fake_hydrate)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/recommendations/playlists",
            json={"prompt": "  dreamy   electronic focus ", "size": 5},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["prompt"] == "dreamy electronic focus"
    assert [track["track_id"] for track in payload["tracks"]] == [123]
