"""retriever.py — Historical context retrieval for RAG."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy import or_, select

from backend.ai_processing.vector_store import generate_embedding
from backend.database.db import get_db_session
from backend.database.models import Article, StoryGroup

logger = logging.getLogger(__name__)


def _as_aware(dt: datetime | None) -> datetime:
    """Ensure datetimes are timezone-aware for stable recency scoring."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _get_query_embedding(story_group: StoryGroup) -> list[float] | None:
    if story_group.representative_embedding is not None:
        return story_group.representative_embedding

    parts = [
        story_group.neutral_title_en or story_group.neutral_title_fr or story_group.neutral_title_ar or "",
        story_group.primary_title or "",
        (story_group.summary_en or story_group.summary_fr or story_group.summary_ar or "")[:1000],
        (story_group.why_it_matters_en or story_group.why_it_matters_fr or story_group.why_it_matters_ar or "")[:500],
    ]
    combined = " — ".join(p.strip() for p in parts if p and p.strip())
    if not combined:
        return None

    return generate_embedding(combined)


def get_relevant_historical_articles(
    story_group: StoryGroup | int,
    limit: int = 5,
    lookback_days: int = 30,
    similarity_threshold: float = 0.75,
    candidate_limit: int = 75,
) -> list[dict[str, Any]]:
    """
    Retrieve the most relevant historical articles for a story group.

    Ranking score:
      final_score = 0.7 * similarity + 0.3 * recency_score

    Where recency_score is 1.0 for newest and decays linearly to 0.0
    at the lookback window boundary.
    """
    with get_db_session() as session:
        group = story_group
        if isinstance(story_group, int):
            group = session.get(StoryGroup, story_group)

        if group is None:
            logger.warning("StoryGroup input is invalid: %s", story_group)
            return []

        query_embedding = _get_query_embedding(group)
        if query_embedding is None:
            logger.warning("StoryGroup %d has no embedding/query text", group.id)
            return []

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=lookback_days)

        distance_expr = Article.embedding.cosine_distance(query_embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        stmt = (
            select(
                Article.id,
                Article.title,
                Article.url,
                Article.source_name,
                Article.language,
                Article.group_id,
                Article.published_at,
                Article.collected_at,
                similarity_expr,
            )
            .where(Article.embedding.isnot(None))
            .where(Article.collected_at >= window_start)
            .where(or_(Article.group_id.is_(None), Article.group_id != group.id))
            .where(similarity_expr >= similarity_threshold)
            .order_by(distance_expr)
            .limit(candidate_limit)
        )

        rows = session.execute(stmt).all()

        max_age_seconds = float(lookback_days * 24 * 60 * 60)
        scored: list[dict[str, Any]] = []

        for row in rows:
            similarity = float(row.similarity)
            timestamp = _as_aware(row.published_at or row.collected_at)
            age_seconds = max(0.0, (now - timestamp).total_seconds())

            recency_score = float(1.0 - np.clip(age_seconds / max_age_seconds, 0.0, 1.0))
            final_score = (0.7 * similarity) + (0.3 * recency_score)

            scored.append(
                {
                    "id": row.id,
                    "title": row.title,
                    "url": row.url,
                    "source_name": row.source_name,
                    "language": row.language,
                    "group_id": row.group_id,
                    "similarity": round(similarity, 4),
                    "recency_score": round(recency_score, 4),
                    "final_score": round(final_score, 4),
                }
            )

        scored.sort(key=lambda item: (item["final_score"], item["similarity"]), reverse=True)
        return scored[:limit]
