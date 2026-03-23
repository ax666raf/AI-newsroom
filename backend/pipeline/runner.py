"""runner.py — Orchestrates the full collection → deduplication pipeline.

Pipeline steps:
  1. Collect  — RSS feeds (ar/en) + NewsAPI (ar/fr/en)
  2. Enrich   — Scrape full text for articles missing it
  3. Deduplicate — URL hash check, then fuzzy/semantic dedup
  4. Persist  — Save new articles to the database
  5. Log      — Write a CollectionLog entry

AI processing (summarisation, rewriting) is done separately by
the ai_processing module which reads from the DB.
"""

import logging
from datetime import datetime, timezone

from backend.database.db import get_db_session
from backend.database.models import Article, CollectionLog
from backend.collector.rss_collector import fetch_all_rss
from backend.collector.api_collector import fetch_all_newsapi
from backend.collector.scraper import enrich_articles
from backend.deduplication.url_hash import filter_known_urls
from backend.deduplication.fuzzy_match import deduplicate_by_title

logger = logging.getLogger(__name__)


def run_pipeline(top_up: bool = False) -> dict:
    """
    Execute one full collection cycle.

    Args:
        top_up: If True, only collect from fast sources (RSS) and skip
                expensive scraping. Used for midday / evening runs.

    Returns:
        Summary dict {articles_found, duplicates, new_stories, status}
    """
    logger.info("Pipeline started (top_up=%s)", top_up)
    run_at = datetime.now(timezone.utc)
    status = "success"
    notes = ""

    # ──────────────────────────────────────────── Step 1: Collect
    try:
        raw = fetch_all_rss()
        if not top_up:
            raw += fetch_all_newsapi()
    except Exception as exc:  # noqa: BLE001
        logger.error("Collection failed: %s", exc)
        status = "failed"
        notes = str(exc)
        raw = []

    articles_found = len(raw)
    logger.info("Collected %d raw articles", articles_found)

    if not raw:
        _write_log(run_at, articles_found, 0, 0, status, notes)
        return {"articles_found": 0, "duplicates": 0, "new_stories": 0, "status": status}

    # ──────────────────────────────────────────── Step 2: URL-hash dedup (fast)
    new_articles = filter_known_urls(raw)
    url_dupes = articles_found - len(new_articles)
    logger.info("After URL dedup: %d new, %d duplicates", len(new_articles), url_dupes)

    # ──────────────────────────────────────────── Step 3: Fuzzy-title dedup
    new_articles = deduplicate_by_title(new_articles)
    title_dupes = (articles_found - url_dupes) - len(new_articles)
    total_dupes = url_dupes + title_dupes
    logger.info("After title dedup: %d articles remain", len(new_articles))

    # ──────────────────────────────────────────── Step 4: Enrich (scrape full text)
    if not top_up:
        new_articles = enrich_articles(new_articles)

    # ──────────────────────────────────────────── Step 5: Persist to DB
    saved = _save_articles(new_articles)
    logger.info("Saved %d new articles to DB", saved)

    _write_log(run_at, articles_found, total_dupes, saved, status, notes)

    return {
        "articles_found": articles_found,
        "duplicates": total_dupes,
        "new_stories": saved,
        "status": status,
    }


def _save_articles(articles: list[dict]) -> int:
    """Bulk-insert articles into the database. Returns count saved."""
    saved = 0
    with get_db_session() as session:
        for data in articles:
            article = Article(
                title=data.get("title"),
                url=data.get("url"),
                url_hash=data.get("url_hash"),
                full_text=data.get("full_text"),
                summary=data.get("summary"),
                source_name=data.get("source_name"),
                language=data.get("language"),
                region=data.get("region", "algeria"),
                category=data.get("category", "general"),
                published_at=data.get("published_at"),
            )
            session.add(article)
            saved += 1
        session.commit()
    return saved


def _write_log(run_at, found, dupes, new, status, notes):
    """Write a CollectionLog entry."""
    with get_db_session() as session:
        log = CollectionLog(
            run_at=run_at,
            articles_found=found,
            duplicates=dupes,
            new_stories=new,
            status=status,
            notes=notes,
        )
        session.add(log)
        session.commit()
