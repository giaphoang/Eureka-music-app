from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IndexedTrack:
    artifact_index: int
    catalog_key: int
    title: str
    artist: str
    album: str | None
    genre: str | None
    audio_path: Path | None = None
    energy_raw: float | None = None
    tempo_raw: float | None = None
    energy_norm: float = 0.5
    tempo_norm: float = 0.5

    @property
    def source_id(self) -> str:
        return f"fma:{self.catalog_key}"


@dataclass(frozen=True)
class RankedTrack:
    catalog_key: int
    prompt_similarity: float
    mmr_score: float
    transition_cost_from_previous: float | None
