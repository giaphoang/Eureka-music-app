from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.recommendation.embedding_backends import model_signature
from app.recommendation.artifacts import read_manifest
from app.recommendation.engine import engine
from app.recommendation.errors import RecommendationError
from app.recommendation.service import hydrate_recommendations
from app.schemas import RecommendationPlaylistOut, RecommendationRequest, RecommendationStatus

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/status", response_model=RecommendationStatus)
def recommendation_status() -> RecommendationStatus:
    manifest = read_manifest(settings.recommendation_dir)
    try:
        model_backend, model_id = model_signature(
            settings.clap_backend,
            settings.clap_checkpoint,
            settings.clap_audio_model,
            settings.hf_clap_model_id,
        )
        checkpoint_configured = settings.clap_backend.strip().lower() != "laion" or settings.clap_checkpoint is not None
    except RecommendationError:
        model_backend = settings.clap_backend
        model_id = settings.hf_clap_model_id
        checkpoint_configured = False
    return RecommendationStatus(
        enabled=settings.recommendation_enabled,
        device="cpu",
        model_backend=model_backend,
        model_id=model_id,
        artifact_ready=manifest is not None,
        artifact_release=str(manifest.get("release_id")) if manifest else None,
        artifact_loaded=engine.artifacts_loaded,
        model_loaded=engine.model_loaded,
        checkpoint_configured=checkpoint_configured,
        indexed_track_count=int(manifest["track_count"]) if manifest and "track_count" in manifest else None,
    )


@router.post("/playlists", response_model=RecommendationPlaylistOut)
def create_recommendation_playlist(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
) -> RecommendationPlaylistOut:
    try:
        return hydrate_recommendations(db, request.prompt, request.size)
    except RecommendationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
