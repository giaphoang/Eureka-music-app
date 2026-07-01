from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Track
from app.schemas import TrackOut, TrackPage
from app.storage import persist_upload, resolve_audio_path, sanitize_filename

router = APIRouter(prefix="/tracks", tags=["tracks"])


def serialize(track: Track) -> TrackOut:
    return TrackOut(
        id=track.id,
        source_id=track.source_id,
        title=track.title,
        artist=track.artist,
        album=track.album,
        genre=track.genre,
        tags=track.tags,
        duration_ms=track.duration_ms,
        original_name=track.original_name,
        size_bytes=track.size_bytes,
        created_at=track.created_at,
        download_url=f"/api/v1/tracks/{track.id}/download",
    )


@router.get("", response_model=TrackPage)
def list_tracks(
    q: str | None = Query(default=None, max_length=200),
    genre: str | None = Query(default=None, max_length=120),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> TrackPage:
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(or_(Track.title.ilike(term), Track.artist.ilike(term), Track.album.ilike(term)))
    if genre:
        filters.append(Track.genre == genre)

    base = select(Track)
    count_stmt = select(func.count()).select_from(Track)
    if filters:
        base = base.where(*filters)
        count_stmt = count_stmt.where(*filters)

    tracks = db.scalars(base.order_by(Track.id).offset(offset).limit(limit)).all()
    total = db.scalar(count_stmt) or 0
    return TrackPage(items=[serialize(t) for t in tracks], total=total, offset=offset, limit=limit)


@router.get("/{track_id}", response_model=TrackOut)
def get_track(track_id: int, db: Session = Depends(get_db)) -> TrackOut:
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return serialize(track)


@router.get("/{track_id}/download")
def download_track(track_id: int, db: Session = Depends(get_db)) -> FileResponse:
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    path = resolve_audio_path(track.storage_name)
    if not path.is_file():
        raise HTTPException(status_code=410, detail="Audio file is missing")
    return FileResponse(
        path,
        media_type=track.content_type,
        filename=sanitize_filename(track.original_name),
    )


@router.post("", response_model=TrackOut, status_code=status.HTTP_201_CREATED)
async def upload_track(
    audio: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=300),
    artist: str = Form(..., min_length=1, max_length=300),
    album: str | None = Form(default=None, max_length=300),
    genre: str | None = Form(default=None, max_length=120),
    tags: str | None = Form(default=None, max_length=2000),
    duration_ms: int | None = Form(default=None, ge=0),
    db: Session = Depends(get_db),
) -> TrackOut:
    storage_name, checksum, size = await persist_upload(audio)
    track = Track(
        title=title.strip(),
        artist=artist.strip(),
        album=album.strip() if album else None,
        genre=genre.strip() if genre else None,
        tags=tags.strip() if tags else None,
        duration_ms=duration_ms,
        storage_name=storage_name,
        original_name=sanitize_filename(audio.filename or "track.mp3"),
        content_type=audio.content_type or "audio/mpeg",
        size_bytes=size,
        checksum_sha256=checksum,
    )
    db.add(track)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        resolve_audio_path(storage_name).unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="This audio file already exists") from exc
    db.refresh(track)
    return serialize(track)
