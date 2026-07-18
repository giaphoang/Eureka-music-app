from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from app.recommendation.types import IndexedTrack, RankedTrack


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    array = np.asarray(vectors, dtype=np.float32)
    if array.ndim == 1:
        array = array.reshape(1, -1)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    safe = np.where(norms > 0, norms, 1.0).astype(np.float32)
    normalized = array / safe
    normalized = np.where(norms > 0, normalized, 0.0)
    return np.ascontiguousarray(normalized, dtype=np.float32)


def _finite_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def robust_scale(values: list[float | None], neutral: float = 0.5) -> list[float]:
    finite = np.asarray([float(value) for value in values if _finite_or_none(value) is not None], dtype=np.float32)
    if finite.size == 0:
        return [neutral for _ in values]
    low, high = np.percentile(finite, [5, 95])
    if not math.isfinite(float(low)) or not math.isfinite(float(high)) or abs(float(high - low)) < 1e-12:
        return [neutral for _ in values]
    scaled: list[float] = []
    for value in values:
        number = _finite_or_none(value)
        if number is None:
            scaled.append(neutral)
            continue
        clipped = min(max(number, float(low)), float(high))
        scaled.append(float((clipped - float(low)) / float(high - low)))
    return scaled


def with_normalized_features(tracks: list[IndexedTrack]) -> list[IndexedTrack]:
    energies = robust_scale([track.energy_raw for track in tracks])
    tempos = robust_scale([track.tempo_raw for track in tracks])
    return [
        replace(track, energy_norm=energy, tempo_norm=tempo)
        for track, energy, tempo in zip(tracks, energies, tempos)
    ]


def _norm_text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _allowed(
    track: IndexedTrack,
    selected: list[IndexedTrack],
    max_per_artist: int | None,
    max_per_album: int | None,
) -> bool:
    if any(track.catalog_key == item.catalog_key for item in selected):
        return False
    if max_per_artist is not None:
        artist = _norm_text(track.artist)
        if artist and sum(1 for item in selected if _norm_text(item.artist) == artist) >= max_per_artist:
            return False
    if max_per_album is not None:
        album = _norm_text(track.album)
        if album and sum(1 for item in selected if _norm_text(item.album) == album) >= max_per_album:
            return False
    return True


def _candidate_order(index: int, relevance: np.ndarray, tracks: list[IndexedTrack]) -> tuple[float, int]:
    return (-float(relevance[index]), tracks[index].catalog_key)


def select_mmr(
    tracks: list[IndexedTrack],
    embeddings: np.ndarray,
    relevance: np.ndarray,
    size: int,
    lambda_mmr: float = 0.75,
    max_per_artist: int = 1,
    max_per_album: int = 1,
) -> list[tuple[IndexedTrack, float]]:
    if not 5 <= size <= 10:
        raise ValueError("playlist size must be between 5 and 10")
    if not tracks:
        return []

    normalized_embeddings = l2_normalize(embeddings)
    relevance = np.asarray(relevance, dtype=np.float32)
    stages: list[tuple[int | None, int | None]] = [
        (max_per_artist, max_per_album),
        (max_per_artist, None),
        (2, None),
        (None, None),
    ]
    selected: list[IndexedTrack] = []
    selected_indices: list[int] = []
    scores: dict[int, float] = {}

    for artist_limit, album_limit in stages:
        while len(selected) < size:
            eligible = [
                index
                for index, track in enumerate(tracks)
                if _allowed(track, selected, artist_limit, album_limit)
            ]
            if not eligible:
                break
            if not selected_indices:
                best = min(eligible, key=lambda index: _candidate_order(index, relevance, tracks))
                score = float(relevance[best])
            else:
                selected_matrix = normalized_embeddings[selected_indices]
                mmr_values = []
                for index in eligible:
                    max_similarity = float(np.max(normalized_embeddings[index] @ selected_matrix.T))
                    score = float(lambda_mmr * relevance[index] - (1.0 - lambda_mmr) * max_similarity)
                    mmr_values.append((score, float(relevance[index]), tracks[index].catalog_key, index))
                best_score, _, _, best = max(mmr_values, key=lambda item: (item[0], item[1], -item[2]))
                score = float(best_score)
            selected.append(tracks[best])
            selected_indices.append(best)
            scores[tracks[best].catalog_key] = score
        if len(selected) >= size:
            break

    return [(track, scores[track.catalog_key]) for track in selected]


def transition_cost(a: IndexedTrack, b: IndexedTrack, a_embedding: np.ndarray, b_embedding: np.ndarray) -> float:
    cosine = float(np.clip(np.dot(a_embedding, b_embedding), -1.0, 1.0))
    cost = (
        0.6 * (1.0 - cosine)
        + 0.2 * abs(float(a.energy_norm) - float(b.energy_norm))
        + 0.2 * abs(float(a.tempo_norm) - float(b.tempo_norm))
    )
    return max(0.0, float(cost))


def order_smoothly(
    selected: list[tuple[IndexedTrack, float]],
    embeddings: np.ndarray,
    relevance_by_key: dict[int, float],
) -> list[RankedTrack]:
    if not selected:
        return []

    by_key = {track.catalog_key: (track, score) for track, score in selected}
    normalized_embeddings = l2_normalize(embeddings)
    remaining = [track for track, _ in selected]
    first = max(remaining, key=lambda track: (relevance_by_key[track.catalog_key], -track.catalog_key))
    ordered = [RankedTrack(first.catalog_key, relevance_by_key[first.catalog_key], by_key[first.catalog_key][1], None)]
    remaining.remove(first)
    previous = first

    while remaining:
        previous_embedding = normalized_embeddings[previous.artifact_index]
        next_track = min(
            remaining,
            key=lambda track: (
                transition_cost(previous, track, previous_embedding, normalized_embeddings[track.artifact_index]),
                -relevance_by_key[track.catalog_key],
                track.catalog_key,
            ),
        )
        cost = transition_cost(previous, next_track, previous_embedding, normalized_embeddings[next_track.artifact_index])
        ordered.append(
            RankedTrack(
                next_track.catalog_key,
                relevance_by_key[next_track.catalog_key],
                by_key[next_track.catalog_key][1],
                cost,
            )
        )
        remaining.remove(next_track)
        previous = next_track
    return ordered
