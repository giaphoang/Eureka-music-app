from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.recommendation.types import IndexedTrack


def text(value: object) -> str | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip()
    return normalized or None


def locate_fma(root: Path) -> tuple[Path, Path]:
    candidates = [
        (root / "fma_small", root / "fma_metadata" / "tracks.csv"),
        (root / "fma_small", root / "tracks.csv"),
        (root, root.parent / "fma_metadata" / "tracks.csv"),
    ]
    for audio_root, tracks_csv in candidates:
        if audio_root.is_dir() and tracks_csv.is_file():
            return audio_root, tracks_csv
    raise FileNotFoundError("Could not find fma_small and fma_metadata/tracks.csv.")


def fma_audio_path(audio_root: Path, track_id: int) -> Path:
    return audio_root / f"{track_id // 1000:03d}" / f"{track_id:06d}.mp3"


def load_fma_tracks(root: Path, limit: int | None = None) -> list[IndexedTrack]:
    audio_root, tracks_csv = locate_fma(root)
    metadata = pd.read_csv(tracks_csv, index_col=0, header=[0, 1])
    small = metadata[metadata[("set", "subset")] == "small"].sort_index()
    if limit:
        small = small.head(limit)

    tracks: list[IndexedTrack] = []
    for artifact_index, (track_id, row) in enumerate(small.iterrows()):
        fma_id = int(track_id)
        tracks.append(
            IndexedTrack(
                artifact_index=artifact_index,
                catalog_key=fma_id,
                title=text(row[("track", "title")]) or f"Track {fma_id}",
                artist=text(row[("artist", "name")]) or "Unknown Artist",
                album=text(row[("album", "title")]),
                genre=text(row[("track", "genre_top")]),
                audio_path=fma_audio_path(audio_root, fma_id),
            )
        )
    return tracks
