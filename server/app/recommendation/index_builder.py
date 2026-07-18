from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import time
import warnings
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from app.recommendation.embedding_backends import get_embedder, model_signature
from app.recommendation.fma_loader import load_fma_tracks
from app.recommendation.rerank import l2_normalize, with_normalized_features
from app.recommendation.types import IndexedTrack


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _audio_features(path: Path) -> tuple[float | None, float | None]:
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError("librosa is required to build recommendation artifacts.") from exc

    y, sr = librosa.load(path, sr=22050, mono=True)
    if y.size == 0:
        return None, None
    rms = librosa.feature.rms(y=y)[0]
    energy = float(np.nanmean(rms)) if rms.size else None
    try:
        tempo_func = getattr(getattr(librosa.feature, "rhythm", None), "tempo", librosa.beat.tempo)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning, message=r"librosa\.beat\.tempo.*")
            tempo_raw = tempo_func(y=y, sr=sr, aggregate=None)
        tempo = float(np.nanmedian(tempo_raw)) if len(tempo_raw) else None
    except Exception:
        tempo = None
    if energy is not None and not math.isfinite(energy):
        energy = None
    if tempo is not None and not math.isfinite(tempo):
        tempo = None
    return energy, tempo


def _write_jsonl(path: Path, tracks: list[IndexedTrack]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for track in tracks:
            row = asdict(track)
            row.pop("audio_path", None)
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_release(release_dir: Path) -> dict[str, Any]:
    manifest_path = release_dir / "manifest.json"
    metadata_path = release_dir / "metadata.jsonl"
    embeddings_path = release_dir / "embeddings.npy"
    faiss_path = release_dir / "songs.faiss"
    for path in (manifest_path, metadata_path, embeddings_path, faiss_path):
        if not path.is_file():
            raise RuntimeError(f"Missing artifact file: {path.name}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    embeddings = np.load(embeddings_path, mmap_mode="r")
    rows = [line for line in metadata_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if embeddings.dtype != np.float32 or embeddings.ndim != 2:
        raise RuntimeError("embeddings.npy must be a float32 matrix")
    if embeddings.shape[0] != len(rows):
        raise RuntimeError("metadata and embedding counts differ")
    if int(manifest.get("track_count", -1)) != len(rows):
        raise RuntimeError("manifest track_count does not match metadata")
    norms = np.linalg.norm(np.asarray(embeddings), axis=1)
    if not np.all(np.isfinite(norms)) or not np.allclose(norms, 1.0, atol=1e-3):
        raise RuntimeError("embeddings are not finite normalized vectors")
    try:
        import faiss
    except ImportError as exc:
        raise RuntimeError("faiss-cpu is required to validate recommendation artifacts") from exc
    index = faiss.read_index(str(faiss_path))
    if index.ntotal != embeddings.shape[0]:
        raise RuntimeError("FAISS index cardinality does not match embeddings")
    return manifest


def publish_release(output_dir: Path, temp_release: Path, release_id: str) -> Path:
    releases = output_dir / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    final_release = releases / release_id
    os.replace(temp_release, final_release)
    current_tmp = output_dir / "CURRENT.tmp"
    current_tmp.write_text(release_id + "\n", encoding="utf-8")
    os.replace(current_tmp, output_dir / "CURRENT")
    return final_release


def build_recommendation_index(
    fma_root: Path,
    output_dir: Path,
    backend: str,
    checkpoint: Path | None,
    audio_model: str,
    hf_model_id: str,
    hf_cache_dir: Path | None,
    threads: int,
    batch_size: int,
    limit: int | None,
) -> dict[str, Any]:
    started = time.monotonic()
    release_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tracks = load_fma_tracks(fma_root, limit=limit)
    embedding_backend, model_id = model_signature(backend, checkpoint, audio_model, hf_model_id)
    clap = get_embedder(
        backend=embedding_backend,
        checkpoint=checkpoint,
        audio_model=audio_model,
        threads=threads,
        hf_model_id=hf_model_id,
        hf_cache_dir=hf_cache_dir,
    )

    built: list[IndexedTrack] = []
    embeddings: list[np.ndarray] = []
    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f".{release_id}.", dir=output_dir) as tmp_name:
        temp_release = Path(tmp_name)
        for offset in range(0, len(tracks), batch_size):
            batch = tracks[offset : offset + batch_size]
            playable = [track for track in batch if track.audio_path and track.audio_path.is_file()]
            for missing in [track for track in batch if track not in playable]:
                failures.append({"catalog_key": missing.catalog_key, "reason": "missing_audio"})
            if not playable:
                continue
            try:
                vectors = clap.embed_audio_files([track.audio_path for track in playable if track.audio_path])
            except Exception as exc:
                for track in playable:
                    failures.append({"catalog_key": track.catalog_key, "reason": str(exc)})
                continue
            for local_index, track in enumerate(playable):
                try:
                    energy, tempo = _audio_features(track.audio_path) if track.audio_path else (None, None)
                    built.append(
                        replace(
                            track,
                            artifact_index=len(built),
                            energy_raw=energy,
                            tempo_raw=tempo,
                        )
                    )
                    embeddings.append(vectors[local_index])
                except Exception as exc:
                    failures.append({"catalog_key": track.catalog_key, "reason": str(exc)})
            if built and len(built) % 100 == 0:
                print(f"Embedded {len(built)} tracks...")

        if not built:
            raise RuntimeError("No recommendation tracks were embedded.")
        built = with_normalized_features(built)
        matrix = l2_normalize(np.vstack(embeddings).astype(np.float32))
        np.save(temp_release / "embeddings.npy", matrix)
        try:
            import faiss
        except ImportError as exc:
            raise RuntimeError("faiss-cpu is required to build recommendation artifacts") from exc
        index = faiss.IndexFlatIP(int(matrix.shape[1]))
        index.add(matrix)
        faiss.write_index(index, str(temp_release / "songs.faiss"))
        _write_jsonl(temp_release / "metadata.jsonl", built)
        with (temp_release / "failed_tracks.jsonl").open("w", encoding="utf-8") as handle:
            for failure in failures:
                handle.write(json.dumps(failure, sort_keys=True) + "\n")
        manifest = {
            "algorithm_version": 1,
            "release_id": release_id,
            "build_timestamp": datetime.now(timezone.utc).isoformat(),
            "embedding_backend": embedding_backend,
            "model_id": model_id,
            "checkpoint_filename": checkpoint.name if checkpoint is not None else None,
            "checkpoint_sha256": file_sha256(checkpoint) if checkpoint is not None else None,
            "audio_model": audio_model,
            "hf_model_id": hf_model_id,
            "embedding_dimension": int(matrix.shape[1]),
            "track_count": len(built),
            "skipped_count": len(failures),
            "fma_root": str(fma_root),
            "limit": limit,
            "threads": threads,
            "batch_size": batch_size,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        _write_manifest(temp_release / "manifest.json", manifest)
        validate_release(temp_release)
        final_release = publish_release(output_dir, temp_release, release_id)
    return validate_release(final_release)
