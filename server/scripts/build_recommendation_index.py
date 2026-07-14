#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.recommendation.index_builder import build_recommendation_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CPU CLAP recommendation artifacts from FMA Small")
    parser.add_argument("fma_root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--backend", choices=("hf", "laion"), default="hf")
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--audio-model", default="HTSAT-base")
    parser.add_argument("--hf-model-id", default="laion/clap-htsat-unfused")
    parser.add_argument("--hf-cache-dir", type=Path, default=None)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true", help="Reserved for shard resume compatibility")
    args = parser.parse_args()
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        manifest = build_recommendation_index(
            fma_root=args.fma_root.expanduser().resolve(),
            output_dir=args.output_dir.expanduser().resolve(),
            backend=args.backend,
            checkpoint=args.checkpoint.expanduser().resolve() if args.checkpoint is not None else None,
            audio_model=args.audio_model,
            hf_model_id=args.hf_model_id,
            hf_cache_dir=args.hf_cache_dir.expanduser().resolve() if args.hf_cache_dir is not None else None,
            threads=max(1, args.threads),
            batch_size=max(1, args.batch_size),
            limit=args.limit,
        )
    except Exception as exc:
        print(f"Recommendation index build failed: {exc}", file=sys.stderr)
        return 1
    print(
        "Done: release={release_id} tracks={track_count} skipped={skipped_count} "
        "elapsed_seconds={elapsed_seconds}".format(**manifest)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
