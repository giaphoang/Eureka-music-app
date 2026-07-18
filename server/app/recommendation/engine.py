from __future__ import annotations

import threading
from collections import OrderedDict

import numpy as np

from app.config import settings
from app.recommendation.artifacts import RecommendationArtifacts, load_artifacts
from app.recommendation.embedding_backends import get_embedder, is_model_loaded, model_signature
from app.recommendation.errors import RecommendationConfigError, RecommendationUnavailable
from app.recommendation.rerank import order_smoothly, select_mmr
from app.recommendation.types import RankedTrack


class RecommendationEngine:
    def __init__(self) -> None:
        self._artifact_lock = threading.Lock()
        self._artifacts: RecommendationArtifacts | None = None
        self._cache: OrderedDict[tuple[str, int], list[RankedTrack]] = OrderedDict()

    @property
    def artifacts_loaded(self) -> bool:
        return self._artifacts is not None

    @property
    def model_loaded(self) -> bool:
        return is_model_loaded()

    def _load_artifacts(self) -> RecommendationArtifacts:
        with self._artifact_lock:
            if self._artifacts is None:
                self._artifacts = load_artifacts(settings.recommendation_dir)
            return self._artifacts

    def recommend(self, prompt: str, size: int) -> list[RankedTrack]:
        if not settings.recommendation_enabled:
            raise RecommendationUnavailable("Recommendation feature is disabled.")
        cache_key = (prompt, size)
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._cache.move_to_end(cache_key)
            return cached

        artifacts = self._load_artifacts()
        if artifacts.count == 0:
            raise RecommendationUnavailable("Recommendation index is empty.")
        expected_backend, expected_model = model_signature(
            settings.clap_backend,
            settings.clap_checkpoint,
            settings.clap_audio_model,
            settings.hf_clap_model_id,
        )
        artifact_backend = str(artifacts.manifest.get("embedding_backend") or "laion")
        artifact_model = str(
            artifacts.manifest.get("model_id")
            or f"{artifacts.manifest.get('audio_model', '')}:{artifacts.manifest.get('checkpoint_filename', '')}"
        )
        if (artifact_backend, artifact_model) != (expected_backend, expected_model):
            raise RecommendationConfigError(
                "Recommendation index was built with a different CLAP model; rebuild the index before querying."
            )
        clap = get_embedder(
            settings.clap_backend,
            settings.clap_checkpoint,
            settings.clap_audio_model,
            settings.clap_threads,
            settings.hf_clap_model_id,
            settings.hf_clap_cache_dir,
        )
        query = clap.embed_text(prompt)
        candidate_count = min(max(size, settings.recommendation_candidates), artifacts.count)
        distances, raw_indices = artifacts.index.search(query.reshape(1, -1), candidate_count)
        indices = np.asarray([int(index) for index in raw_indices[0] if int(index) >= 0], dtype=np.int64)
        scores = np.asarray(distances[0][: len(indices)], dtype=np.float32)
        candidates = [artifacts.tracks[int(index)] for index in indices]
        candidate_embeddings = np.asarray(artifacts.embeddings[indices], dtype=np.float32)
        relevance = scores
        selected = select_mmr(
            candidates,
            candidate_embeddings,
            relevance,
            size=size,
            lambda_mmr=settings.mmr_lambda,
            max_per_artist=settings.max_per_artist,
            max_per_album=settings.max_per_album,
        )
        relevance_by_key = {track.catalog_key: float(score) for track, score in zip(candidates, relevance)}

        full_embeddings = np.zeros_like(artifacts.embeddings)
        for local_index, artifact_index in enumerate(indices):
            full_embeddings[int(artifact_index)] = candidate_embeddings[local_index]
        ranked = order_smoothly(selected, full_embeddings, relevance_by_key)
        if len(ranked) < size:
            raise RecommendationUnavailable("Recommendation index could not produce enough tracks.")

        self._cache[cache_key] = ranked
        while len(self._cache) > max(1, settings.prompt_cache_size):
            self._cache.popitem(last=False)
        return ranked


engine = RecommendationEngine()
