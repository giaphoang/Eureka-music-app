from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.recommendation.errors import RecommendationUnavailable
from app.recommendation.rerank import l2_normalize, with_normalized_features
from app.recommendation.types import IndexedTrack


@dataclass(frozen=True)
class RecommendationArtifacts:
    root: Path
    release_id: str
    manifest: dict[str, Any]
    tracks: list[IndexedTrack]
    embeddings: np.ndarray
    index: object

    @property
    def count(self) -> int:
        return len(self.tracks)

    @property
    def dimension(self) -> int:
        return int(self.embeddings.shape[1])


def current_release_dir(root: Path) -> Path:
    current = root / "CURRENT"
    if not current.is_file():
        raise RecommendationUnavailable("Recommendation artifacts are not published.")
    release_id = current.read_text(encoding="utf-8").strip()
    if not release_id or "/" in release_id:
        raise RecommendationUnavailable("Recommendation CURRENT pointer is invalid.")
    release_dir = root / "releases" / release_id
    if not release_dir.is_dir():
        raise RecommendationUnavailable("Recommendation release directory is missing.")
    return release_dir


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except OSError as exc:
        raise RecommendationUnavailable(f"Recommendation artifact is unreadable: {path.name}") from exc
    if not isinstance(value, dict):
        raise RecommendationUnavailable(f"Recommendation artifact is invalid: {path.name}")
    return value


def _read_metadata(path: Path) -> list[IndexedTrack]:
    tracks: list[IndexedTrack] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                tracks.append(
                    IndexedTrack(
                        artifact_index=int(row["artifact_index"]),
                        catalog_key=int(row["catalog_key"]),
                        title=str(row.get("title") or f"Track {row['catalog_key']}"),
                        artist=str(row.get("artist") or "Unknown Artist"),
                        album=str(row["album"]) if row.get("album") else None,
                        genre=str(row["genre"]) if row.get("genre") else None,
                        energy_raw=row.get("energy_raw"),
                        tempo_raw=row.get("tempo_raw"),
                    )
                )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RecommendationUnavailable(f"Recommendation metadata is invalid near line {line_number}.") from exc
    return with_normalized_features(tracks)


def load_artifacts(root: Path) -> RecommendationArtifacts:
    release_dir = current_release_dir(root)
    manifest = _read_json(release_dir / "manifest.json")
    metadata_path = release_dir / "metadata.jsonl"
    embeddings_path = release_dir / "embeddings.npy"
    faiss_path = release_dir / "songs.faiss"
    if not embeddings_path.is_file():
        raise RecommendationUnavailable("Recommendation embeddings file is missing.")
    if not faiss_path.is_file():
        raise RecommendationUnavailable("Recommendation FAISS index is missing.")

    tracks = _read_metadata(metadata_path)
    try:
        embeddings = np.load(embeddings_path, mmap_mode="r")
    except OSError as exc:
        raise RecommendationUnavailable("Recommendation embeddings file is unreadable.") from exc
    if embeddings.ndim != 2 or embeddings.dtype != np.float32:
        raise RecommendationUnavailable("Recommendation embeddings must be a float32 matrix.")
    if embeddings.shape[0] != len(tracks):
        raise RecommendationUnavailable("Recommendation metadata and embedding counts differ.")
    if len({track.artifact_index for track in tracks}) != len(tracks):
        raise RecommendationUnavailable("Recommendation metadata contains duplicate artifact indices.")
    if sorted(track.artifact_index for track in tracks) != list(range(len(tracks))):
        raise RecommendationUnavailable("Recommendation artifact indices are not contiguous.")

    norms = np.linalg.norm(np.asarray(embeddings), axis=1)
    if not np.all(np.isfinite(norms)):
        raise RecommendationUnavailable("Recommendation embeddings contain non-finite values.")
    if not np.allclose(norms, 1.0, atol=1e-3):
        raise RecommendationUnavailable("Recommendation embeddings are not normalized.")
    try:
        import faiss
    except ImportError as exc:
        raise RecommendationUnavailable("faiss-cpu is not installed in the server environment.") from exc
    index = faiss.read_index(str(faiss_path))
    if index.ntotal != len(tracks):
        raise RecommendationUnavailable("Recommendation FAISS index and metadata counts differ.")

    return RecommendationArtifacts(
        root=root,
        release_id=release_dir.name,
        manifest=manifest,
        tracks=tracks,
        embeddings=l2_normalize(np.asarray(embeddings)),
        index=index,
    )


def read_manifest(root: Path) -> dict[str, Any] | None:
    try:
        return _read_json(current_release_dir(root) / "manifest.json")
    except RecommendationUnavailable:
        return None
