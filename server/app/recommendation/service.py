from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Track
from app.recommendation.engine import engine
from app.recommendation.errors import RecommendationStaleIndex
from app.recommendation.types import RankedTrack
from app.routers.tracks import serialize
from app.schemas import RecommendationPlaylistOut, RecommendationTrackOut


def hydrate_recommendations(db: Session, prompt: str, size: int) -> RecommendationPlaylistOut:
    ranked = engine.recommend(prompt, size)
    source_ids = [f"fma:{item.catalog_key}" for item in ranked]
    rows = db.scalars(select(Track).where(Track.source_id.in_(source_ids))).all()
    by_source = {row.source_id: row for row in rows}
    if len(by_source) < len(source_ids):
        raise RecommendationStaleIndex("Recommendation index is stale; rebuild it from the current catalog.")

    items: list[RecommendationTrackOut] = []
    for position, item in enumerate(ranked, start=1):
        track = by_source.get(f"fma:{item.catalog_key}")
        if track is None:
            raise RecommendationStaleIndex("Recommendation index is stale; rebuild it from the current catalog.")
        serialized = serialize(track)
        items.append(
            RecommendationTrackOut(
                position=position,
                track_id=serialized.id,
                title=serialized.title,
                artist=serialized.artist,
                album=serialized.album,
                genre=serialized.genre,
                download_url=serialized.download_url,
                original_name=serialized.original_name,
                duration_ms=serialized.duration_ms,
                prompt_similarity=item.prompt_similarity,
                mmr_score=item.mmr_score,
                transition_cost_from_previous=item.transition_cost_from_previous,
            )
        )

    return RecommendationPlaylistOut(
        prompt=prompt,
        strategy="CLAP cosine retrieval + MMR diversity + smooth transitions",
        tracks=items,
    )
