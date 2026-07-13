from __future__ import annotations

import os
import threading
from pathlib import Path

import numpy as np

from app.recommendation.errors import RecommendationConfigError
from app.recommendation.rerank import l2_normalize


class HuggingFaceClapCPU:
    def __init__(self, model_id: str, threads: int, cache_dir: Path | None = None) -> None:
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        os.environ.setdefault("OMP_NUM_THREADS", str(max(1, threads)))
        os.environ.setdefault("MKL_NUM_THREADS", str(max(1, threads)))

        try:
            import librosa
            import torch
            from transformers import AutoProcessor, ClapModel
        except ImportError as exc:
            raise RecommendationConfigError(
                "Hugging Face CLAP dependencies are not installed in the server environment."
            ) from exc

        self._librosa = librosa
        self._torch = torch
        try:
            torch.set_num_threads(max(1, threads))
        except RuntimeError:
            pass
        self._lock = threading.Lock()
        cache_path = str(cache_dir) if cache_dir is not None else None
        self._processor = AutoProcessor.from_pretrained(model_id, cache_dir=cache_path)
        self._model = ClapModel.from_pretrained(model_id, cache_dir=cache_path)
        self._model = self._model.to("cpu")
        self._model.eval()
        self._assert_cpu()

    def _assert_cpu(self) -> None:
        try:
            parameter = next(self._model.parameters())
        except StopIteration:
            return
        if parameter.device.type != "cpu":
            raise RecommendationConfigError("Hugging Face CLAP model is not running on CPU.")

    def embed_text(self, prompt: str) -> np.ndarray:
        with self._lock, self._torch.inference_mode():
            self._assert_cpu()
            inputs = self._processor(text=[prompt], return_tensors="pt", padding=True)
            features = self._model.get_text_features(**inputs)
        return l2_normalize(features.detach().cpu().numpy().astype(np.float32))[0]

    def embed_audio_files(self, paths: list[Path]) -> np.ndarray:
        waves = [self._librosa.load(path, sr=48_000, mono=True)[0] for path in paths]
        with self._lock, self._torch.inference_mode():
            self._assert_cpu()
            inputs = self._processor(audio=waves, sampling_rate=48_000, return_tensors="pt", padding=True)
            features = self._model.get_audio_features(**inputs)
        return l2_normalize(features.detach().cpu().numpy().astype(np.float32))


_singleton: HuggingFaceClapCPU | None = None
_singleton_key: tuple[str, int, Path | None] | None = None
_singleton_lock = threading.Lock()


def get_hf_clap(model_id: str, threads: int, cache_dir: Path | None = None) -> HuggingFaceClapCPU:
    global _singleton, _singleton_key
    key = (model_id, threads, cache_dir)
    if _singleton is not None and _singleton_key == key:
        return _singleton
    with _singleton_lock:
        if _singleton is None or _singleton_key != key:
            _singleton = HuggingFaceClapCPU(model_id=model_id, threads=threads, cache_dir=cache_dir)
            _singleton_key = key
    return _singleton
