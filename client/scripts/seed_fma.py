#!/usr/bin/env python3
import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eureka_client.config import DOWNLOAD_DIR, ensure_dirs
from eureka_client.db import ClientDB


def text(value: object) -> str | None:
    if pd.isna(value):
        return None
    result = str(value).strip()
    return result or None


def locate(root: Path) -> tuple[Path, Path]:
    candidates = [
        (root / "fma_small", root / "fma_metadata" / "tracks.csv"),
        (root / "fma_small", root / "tracks.csv"),
        (root, root.parent / "fma_metadata" / "tracks.csv"),
    ]
    for audio_root, tracks_csv in candidates:
        if audio_root.is_dir() and tracks_csv.is_file():
            return audio_root, tracks_csv
    raise SystemExit("Could not locate fma_small and tracks.csv")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local SQLite/download store from FMA Small")
    parser.add_argument("fma_root", type=Path)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--copy", action="store_true")
    args = parser.parse_args()

    audio_root, tracks_csv = locate(args.fma_root.expanduser().resolve())
    metadata = pd.read_csv(tracks_csv, index_col=0, header=[0, 1])
    small = metadata[metadata[("set", "subset")] == "small"]
    if args.limit:
        small = small.head(args.limit)

    ensure_dirs()
    db = ClientDB()
    count = 0
    for track_id, row in small.iterrows():
        src = audio_root / f"{int(track_id) // 1000:03d}" / f"{int(track_id):06d}.mp3"
        if not src.is_file():
            continue
        dst = DOWNLOAD_DIR / src.name
        if not dst.exists():
            try:
                if args.copy:
                    raise OSError
                dst.hardlink_to(src)
            except OSError:
                shutil.copy2(src, dst)
        db.upsert_download(
            {
                "id": -int(track_id),  # negative IDs avoid collision with server track IDs
                "title": text(row[("track", "title")]) or f"Track {track_id}",
                "artist": text(row[("artist", "name")]) or "Unknown Artist",
                "album": text(row[("album", "title")]),
                "genre": text(row[("track", "genre_top")]),
                "duration_ms": int(float(row[("track", "duration")]) * 1000)
                if not pd.isna(row[("track", "duration")])
                else 30_000,
            },
            str(dst),
        )
        count += 1
    print(f"Seeded {count} downloaded tracks into {db.path}")


if __name__ == "__main__":
    main()
