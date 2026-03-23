"""embeddings.py — Ingestion helpers for generating/storing article vectors."""

import logging

from backend.ai_processing.vector_store import embed_article, embed_unprocessed_articles

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
