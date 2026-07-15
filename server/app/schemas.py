from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
