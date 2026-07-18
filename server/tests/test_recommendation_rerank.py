from __future__ import annotations

import numpy as np
import pytest

from app.recommendation.rerank import l2_normalize, order_smoothly, robust_scale, select_mmr
from app.recommendation.types import IndexedTrack


def track(
    key: int,
    *,
    artist: str = "Artist",
    album: str = "Album",
    energy: float | None = 0.5,
    tempo: float | None = 0.5,
) -> IndexedTrack:
    return IndexedTrack(
        artifact_index=key - 1,
        catalog_key=key,
        title=f"Track {key}",
        artist=artist,
        album=album,
        genre="Rock",
        energy_norm=0.5 if energy is None else energy,
        tempo_norm=0.5 if tempo is None else tempo,
    )


def test_l2_normalize_handles_zero_vectors() -> None:
    normalized = l2_normalize(np.asarray([[3.0, 4.0], [0.0, 0.0]], dtype=np.float32))

    assert np.allclose(normalized[0], [0.6, 0.8])
    assert np.allclose(normalized[1], [0.0, 0.0])
    assert normalized.dtype == np.float32


def test_robust_scale_handles_missing_and_identical_values() -> None:
    assert robust_scale([None, float("nan"), float("inf")]) == [0.5, 0.5, 0.5]
    assert robust_scale([4.0, 4.0, 4.0]) == [0.5, 0.5, 0.5]

    scaled = robust_scale([0.0, 1.0, 100.0, None])

    assert scaled[0] == pytest.approx(0.0)
    assert 0.0 < scaled[1] < 1.0
    assert scaled[2] == pytest.approx(1.0)
    assert scaled[3] == pytest.approx(0.5)


def test_mmr_applies_constraints_relaxes_deterministically_and_avoids_duplicates() -> None:
    tracks = [
        track(1, artist="Same", album="Same"),
        track(2, artist="Same", album="Other"),
        track(3, artist="Third", album="Third"),
        track(4, artist="Fourth", album="Fourth"),
        track(5, artist="Fifth", album="Fifth"),
        track(6, artist="Sixth", album="Sixth"),
    ]
    embeddings = l2_normalize(
        np.asarray(
            [
                [1.0, 0.0, 0.0],
                [0.9, 0.1, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.7, 0.7, 0.0],
                [0.2, 0.2, 0.8],
            ],
            dtype=np.float32,
        )
    )
    relevance = np.asarray([0.99, 0.98, 0.70, 0.69, 0.68, 0.67], dtype=np.float32)

    selected = select_mmr(tracks, embeddings, relevance, size=6)
    keys = [item.catalog_key for item, _ in selected]

    assert keys[0] == 1
    assert len(keys) == len(set(keys)) == 6
    assert keys.count(2) == 1


def test_transition_order_starts_with_highest_relevance_and_imputes_features() -> None:
    tracks = [
        track(1, energy=0.0, tempo=0.0),
        track(2, energy=None, tempo=None),
        track(3, energy=1.0, tempo=1.0),
        track(4, energy=0.2, tempo=0.2),
        track(5, energy=0.8, tempo=0.8),
    ]
    embeddings = l2_normalize(
        np.asarray(
            [
                [1.0, 0.0],
                [0.9, 0.1],
                [0.0, 1.0],
                [0.7, 0.3],
                [0.2, 0.8],
            ],
            dtype=np.float32,
        )
    )
    selected = [(item, 0.1) for item in tracks]
    relevance_by_key = {1: 0.7, 2: 0.99, 3: 0.6, 4: 0.5, 5: 0.4}

    ordered = order_smoothly(selected, embeddings, relevance_by_key)

    assert ordered[0].catalog_key == 2
    assert ordered[0].transition_cost_from_previous is None
    assert all(item.transition_cost_from_previous is None or item.transition_cost_from_previous >= 0 for item in ordered)


def test_playlist_size_boundaries() -> None:
    tracks = [track(index) for index in range(1, 7)]
    embeddings = np.eye(6, dtype=np.float32)
    relevance = np.linspace(1.0, 0.1, 6, dtype=np.float32)

    with pytest.raises(ValueError):
        select_mmr(tracks, embeddings, relevance, size=4)
    with pytest.raises(ValueError):
        select_mmr(tracks, embeddings, relevance, size=11)
