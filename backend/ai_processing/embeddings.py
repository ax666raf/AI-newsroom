"""embeddings.py — Ingestion helpers for generating/storing article vectors."""

import logging
from sqlalchemy import select

from backend.ai_processing.vector_store import (
    embed_article,
    embed_unprocessed_articles,
    generate_embedding,
)
from backend.database.db import get_db_session
from backend.database.models import StoryGroup

logger = logging.getLogger(__name__)


def embed_new_article(article_id: int) -> bool:
    """Generate and store an embedding for one newly ingested article."""
    return embed_article(article_id)


def embed_new_articles(article_ids: list[int]) -> int:
    """Generate/store embeddings for a batch of newly ingested article IDs."""
    if not article_ids:
        return 0

    embedded = 0
    for article_id in article_ids:
        if embed_article(article_id):
            embedded += 1

    logger.info("Embedded %d/%d newly ingested articles", embedded, len(article_ids))
    return embedded


def embed_latest_unprocessed(limit: int = 200) -> int:
    """Backfill embeddings for articles that still do not have vectors."""
    return embed_unprocessed_articles(limit=limit)


def generate_story_group_embedding(story_group: StoryGroup) -> list[float] | None:
    """
    Build a representative embedding for a StoryGroup.

    Uses the same MiniLM model used by semantic deduplication.
    Returns a Python list so it can be written directly to pgvector columns.
    """
    parts = [
        story_group.neutral_title or "",
        story_group.primary_title or "",
        (story_group.summary or "")[:1000],
        (story_group.why_it_matters or "")[:500],
    ]

    combined = " — ".join(p.strip() for p in parts if p and p.strip())
    if not combined:
        return None

    return generate_embedding(combined)


def embed_story_group(group_id: int) -> bool:
    """Generate/store an embedding for a single StoryGroup."""
    with get_db_session() as session:
        group = session.get(StoryGroup, group_id)
        if group is None:
            logger.warning("StoryGroup %d not found", group_id)
            return False

        if group.representative_embedding is not None:
            logger.debug("StoryGroup %d already has representative_embedding", group_id)
            return True

        embedding = generate_story_group_embedding(group)
        if embedding is None:
            logger.warning("StoryGroup %d has no useful text to embed", group_id)
            return False

        group.representative_embedding = embedding
        session.commit()
        return True


def embed_unprocessed_story_groups(limit: int = 200) -> int:
    """
    Backfill embeddings for StoryGroups with null representative embeddings.
    """
    with get_db_session() as session:
        stmt = (
            select(StoryGroup)
            .where(StoryGroup.representative_embedding.is_(None))
            .order_by(StoryGroup.updated_at.desc())
            .limit(limit)
        )
        groups = list(session.scalars(stmt))

        if not groups:
            logger.info("No unembedded story groups to process")
            return 0

        embedded = 0
        for group in groups:
            embedding = generate_story_group_embedding(group)
            if embedding is None:
                continue
            group.representative_embedding = embedding
            embedded += 1

        session.commit()
        logger.info("Embedded %d/%d story groups", embedded, len(groups))
        return embedded
