import hashlib
import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import settings

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str) -> str:
    clean = _SAFE_NAME.sub("_", Path(name).name).strip("._")
    return clean or "track.mp3"


def resolve_audio_path(storage_name: str) -> Path:
    root = settings.audio_root.resolve()
    path = (root / storage_name).resolve()
    if root not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid storage path")
    return path


async def persist_upload(upload: UploadFile) -> tuple[str, str, int]:
    settings.audio_root.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "track.mp3").suffix.lower() or ".mp3"
    if suffix not in {".mp3", ".wav", ".ogg", ".m4a", ".flac"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported audio format")

    storage_name = f"{uuid4().hex}{suffix}"
    final_path = resolve_audio_path(storage_name)
    temp_path = final_path.with_suffix(final_path.suffix + ".part")
    digest = hashlib.sha256()
    size = 0

    try:
        with temp_path.open("wb") as out:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail="File is too large")
                digest.update(chunk)
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp_path, final_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    return storage_name, digest.hexdigest(), size
