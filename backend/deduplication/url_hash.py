"""
url_hash.py — Level 1 Deduplication: exact URL matching via SHA-256.

This is the FASTEST dedup layer.  Before any fuzzy or semantic check,
we hash every incoming URL and compare it against hashes already in
the database.  If a hash exists → the article is an exact duplicate.

Complexity: O(n) with a single DB round-trip for the whole batch.
"""

import hashlib
import logging
from typing import Sequence

from sqlalchemy import select

from backend.database.db import get_db_session
from backend.database.models import Article

logger = logging.getLogger(__name__)


def compute_url_hash(url: str) -> str:
    """
    Produce a deterministic SHA-256 hex digest for a URL.

    Normalises the URL first:
      • strip whitespace
      • lowercase
      • remove trailing slash
    """
    normalised = url.strip().lower().rstrip("/")
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def filter_known_urls(articles: list[dict]) -> list[dict]:
    """
    Remove articles whose url_hash already exists in the DB.

    Args:
        articles: list of raw article dicts (must have 'url' key).

    Returns:
        A new list containing only articles NOT yet stored.

    Side effect:
        Re-computes and sets 'url_hash' on every article dict so
        downstream code can rely on it being present and correct.
    """
    if not articles:
        return []

    # (Re-)compute hashes with our canonical normalisation
    for article in articles:
        article["url_hash"] = compute_url_hash(article["url"])

    incoming_hashes = {a["url_hash"] for a in articles}

    # Single query: fetch all hashes that already exist
    with get_db_session() as session:
        stmt = (
            select(Article.url_hash)
            .where(Article.url_hash.in_(incoming_hashes))
        )
        existing_hashes: set[str] = {row[0] for row in session.execute(stmt)}

    # Filter
    new_articles = [a for a in articles if a["url_hash"] not in existing_hashes]

    dupes = len(articles) - len(new_articles)
    logger.info(
        "URL-hash dedup: %d incoming → %d new, %d exact duplicates",
        len(articles), len(new_articles), dupes,
    )
    return new_articles


def url_exists(url: str) -> bool:
    """Check whether a single URL is already in the database."""
    h = compute_url_hash(url)
    with get_db_session() as session:
        stmt = select(Article.id).where(Article.url_hash == h).limit(1)
        return session.execute(stmt).first() is not None
