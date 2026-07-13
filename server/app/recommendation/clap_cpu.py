from __future__ import annotations

import os
import threading
from pathlib import Path

import numpy as np

from app.recommendation.errors import RecommendationConfigError
from app.recommendation.rerank import l2_normalize


class ClapCPU:
    def __init__(self, checkpoint: Path, audio_model: str, threads: int) -> None:
        if not checkpoint.is_file():
            raise RecommendationConfigError("CLAP checkpoint is missing.")
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        os.environ.setdefault("OMP_NUM_THREADS", str(max(1, threads)))
        os.environ.setdefault("MKL_NUM_THREADS", str(max(1, threads)))

        try:
            import torch
            import laion_clap
        except ImportError as exc:
            raise RecommendationConfigError("CLAP dependencies are not installed in the server environment.") from exc

        self._torch = torch
        try:
            torch.set_num_threads(max(1, threads))
        except RuntimeError:
            pass
        self._lock = threading.Lock()
        self._model = laion_clap.CLAP_Module(enable_fusion=False, device="cpu", amodel=audio_model)
        self._model.load_ckpt(str(checkpoint))
        self._model.eval()
        self._assert_cpu()

    def _assert_cpu(self) -> None:
        try:
            parameter = next(self._model.parameters())
        except StopIteration:
            return
        if parameter.device.type != "cpu":
            raise RecommendationConfigError("CLAP model is not running on CPU.")

    def embed_text(self, prompt: str) -> np.ndarray:
        with self._lock, self._torch.inference_mode():
            self._assert_cpu()
            vector = self._model.get_text_embedding([prompt], use_tensor=False)
        return l2_normalize(np.asarray(vector, dtype=np.float32))[0]

    def embed_audio_files(self, paths: list[Path]) -> np.ndarray:
        with self._lock, self._torch.inference_mode():
            self._assert_cpu()
            vectors = self._model.get_audio_embedding_from_filelist(
                x=[str(path) for path in paths],
                use_tensor=False,
            )
        return l2_normalize(np.asarray(vectors, dtype=np.float32))


_singleton: ClapCPU | None = None
_singleton_key: tuple[Path, str, int] | None = None
_singleton_lock = threading.Lock()


def get_clap(checkpoint: Path, audio_model: str, threads: int) -> ClapCPU:
    global _singleton, _singleton_key
    key = (checkpoint, audio_model, threads)
    if _singleton is not None and _singleton_key == key:
        return _singleton
    with _singleton_lock:
        if _singleton is None or _singleton_key != key:
            _singleton = ClapCPU(checkpoint=checkpoint, audio_model=audio_model, threads=threads)
            _singleton_key = key
    return _singleton
