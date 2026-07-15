#!/usr/bin/env python3
import argparse
import hashlib
import shutil
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Track


def text(value: object) -> str | None:
    if pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def locate(root: Path) -> tuple[Path, Path]:
    candidates = [
        (root / "fma_small", root / "fma_metadata" / "tracks.csv"),
        (root / "fma_small", root / "tracks.csv"),
        (root, root.parent / "fma_metadata" / "tracks.csv"),
    ]
    for audio_root, tracks_csv in candidates:
        if audio_root.is_dir() and tracks_csv.is_file():
            return audio_root, tracks_csv
    raise SystemExit(
        "Could not find fma_small and tracks.csv. Pass a directory containing "
        "fma_small/ and fma_metadata/tracks.csv."
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the server from FMA Small")
    parser.add_argument("fma_root", type=Path)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--copy", action="store_true", help="Copy even when hard-linking is possible")
    args = parser.parse_args()

    audio_root, tracks_csv = locate(args.fma_root.expanduser().resolve())
    metadata = pd.read_csv(tracks_csv, index_col=0, header=[0, 1])
    small = metadata[metadata[("set", "subset")] == "small"]
    if args.limit:
        small = small.head(args.limit)

    settings.audio_root.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    inserted = skipped = missing = 0
    with SessionLocal() as db:
        for track_id, row in small.iterrows():
            source_id = f"fma:{int(track_id)}"
            if db.scalar(select(Track.id).where(Track.source_id == source_id)):
                skipped += 1
                continue

            src = audio_root / f"{int(track_id) // 1000:03d}" / f"{int(track_id):06d}.mp3"
            if not src.is_file():
                missing += 1
                continue

            storage_name = f"fma_{int(track_id):06d}.mp3"
            dst = settings.audio_root / storage_name
            if not dst.exists():
                try:
                    if args.copy:
                        raise OSError
                    dst.hardlink_to(src)
                except OSError:
                    shutil.copy2(src, dst)

            checksum = sha256(dst)
            duplicate = db.scalar(select(Track.id).where(Track.checksum_sha256 == checksum))
            if duplicate:
                dst.unlink(missing_ok=True)
                skipped += 1
                continue

            db.add(
                Track(
                    source_id=source_id,
                    title=text(row[("track", "title")]) or f"Track {track_id}",
                    artist=text(row[("artist", "name")]) or "Unknown Artist",
                    album=text(row[("album", "title")]),
                    genre=text(row[("track", "genre_top")]),
                    tags=text(row[("track", "tags")]),
                    duration_ms=int(float(row[("track", "duration")]) * 1000)
                    if not pd.isna(row[("track", "duration")])
                    else 30_000,
                    storage_name=storage_name,
                    original_name=src.name,
                    content_type="audio/mpeg",
                    size_bytes=dst.stat().st_size,
                    checksum_sha256=checksum,
                )
            )
            inserted += 1
            if inserted % 100 == 0:
                db.commit()
                print(f"Inserted {inserted} tracks...")
        db.commit()

    print(f"Done: inserted={inserted}, skipped={skipped}, missing={missing}")


if __name__ == "__main__":
    main()
