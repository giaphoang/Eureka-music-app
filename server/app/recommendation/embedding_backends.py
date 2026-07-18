from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np

from app.recommendation.errors import RecommendationConfigError


class ClapEmbedder(Protocol):
    def embed_text(self, prompt: str) -> np.ndarray:
        ...

    def embed_audio_files(self, paths: list[Path]) -> np.ndarray:
        ...


def model_signature(
    backend: str,
    checkpoint: Path | None,
    audio_model: str,
    hf_model_id: str,
) -> tuple[str, str]:
    normalized = backend.strip().lower()
    if normalized == "hf":
        return ("hf", hf_model_id)
    if normalized == "laion":
        if checkpoint is None:
            raise RecommendationConfigError("CLAP checkpoint is required when EUREKA_CLAP_BACKEND=laion.")
        return ("laion", f"{audio_model}:{checkpoint.name}")
    raise RecommendationConfigError("EUREKA_CLAP_BACKEND must be either 'hf' or 'laion'.")


def get_embedder(
    backend: str,
    checkpoint: Path | None,
    audio_model: str,
    threads: int,
    hf_model_id: str,
    hf_cache_dir: Path | None,
) -> ClapEmbedder:
    normalized = backend.strip().lower()
    if normalized == "hf":
        from app.recommendation.hf_clap import get_hf_clap

        return get_hf_clap(hf_model_id, threads, hf_cache_dir)
    if normalized == "laion":
        if checkpoint is None:
            raise RecommendationConfigError("CLAP checkpoint is required when EUREKA_CLAP_BACKEND=laion.")
        from app.recommendation.clap_cpu import get_clap

        return get_clap(checkpoint, audio_model, threads)
    raise RecommendationConfigError("EUREKA_CLAP_BACKEND must be either 'hf' or 'laion'.")


def is_model_loaded() -> bool:
    from app.recommendation import clap_cpu, hf_clap

    return clap_cpu._singleton is not None or hf_clap._singleton is not None
