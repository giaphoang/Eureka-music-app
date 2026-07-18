from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TrackOut(BaseModel):
    id: int
    source_id: str | None
    title: str
    artist: str
    album: str | None
    genre: str | None
    tags: str | None
    duration_ms: int | None
    original_name: str
    size_bytes: int
    created_at: datetime
    download_url: str

    model_config = ConfigDict(from_attributes=True)


class TrackPage(BaseModel):
    items: list[TrackOut]
    total: int
    offset: int
    limit: int


class RecommendationRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=300)
    size: int = Field(default=10, ge=5, le=10)

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 3:
            raise ValueError("Prompt must contain at least 3 non-whitespace characters.")
        return normalized


class RecommendationStatus(BaseModel):
    enabled: bool
    device: str
    model_backend: str
    model_id: str
    artifact_ready: bool
    artifact_release: str | None
    artifact_loaded: bool
    model_loaded: bool
    checkpoint_configured: bool
    indexed_track_count: int | None


class RecommendationTrackOut(BaseModel):
    position: int
    track_id: int
    title: str
    artist: str
    album: str | None
    genre: str | None
    download_url: str
    original_name: str
    duration_ms: int | None
    prompt_similarity: float
    mmr_score: float
    transition_cost_from_previous: float | None


class RecommendationPlaylistOut(BaseModel):
    prompt: str
    strategy: str
    tracks: list[RecommendationTrackOut]
