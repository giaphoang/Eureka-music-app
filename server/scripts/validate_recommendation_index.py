#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.recommendation.artifacts import current_release_dir
from app.recommendation.index_builder import validate_release


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate published recommendation artifacts")
    parser.add_argument("artifact_root", type=Path)
    args = parser.parse_args()
    try:
        release_dir = current_release_dir(args.artifact_root.expanduser().resolve())
        manifest = validate_release(release_dir)
    except Exception as exc:
        print(f"Recommendation index validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"OK: release={release_dir.name} tracks={manifest['track_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
