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
from email.utils import parsedate_to_datetime
from typing import Any

from backend.database.db import get_db_session
from backend.database.models import Article, CollectionLog
from backend.ai_processing.embeddings import embed_new_articles
from backend.collector.rss_collector import fetch_all_rss
from backend.collector.api_collector import fetch_all_newsapi
from backend.collector.scraper import enrich_articles
from backend.deduplication.url_hash import filter_known_urls
from backend.deduplication.fuzzy_match import deduplicate_by_title
from backend.deduplication.semantic_match import group_article_ids

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
        _write_log(run_at, articles_found, 0, 0, 0, status, notes)
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
    saved_ids = _save_articles(new_articles)
    saved = len(saved_ids)
    logger.info("Saved %d new articles to DB", saved)

    embeddings_generated = 0
    groups_created = 0

    if saved_ids:
        try:
            embeddings_generated = embed_new_articles(saved_ids)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Embedding generation failed: %s", exc)
            status = "partial"
            notes = _append_note(notes, f"embedding_failed={exc}")

        try:
            group_summary = group_article_ids(saved_ids)
            groups_created = int(group_summary.get("groups_created", 0))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Story grouping failed: %s", exc)
            status = "partial"
            notes = _append_note(notes, f"grouping_failed={exc}")

    _write_log(run_at, articles_found, total_dupes, saved, groups_created, status, notes)

    return {
        "articles_found": articles_found,
        "duplicates": total_dupes,
        "new_stories": saved,
        "groups_created": groups_created,
        "embeddings_generated": embeddings_generated,
        "status": status,
    }


def _save_articles(articles: list[dict]) -> list[int]:
    """Bulk-insert articles into DB. Returns inserted article IDs."""
    saved_ids: list[int] = []

    with get_db_session() as session:
        for data in articles:
            normalised = _normalise_article_payload(data)
            if not normalised:
                continue

            article = Article(
                title=normalised["title"],
                url=normalised["url"],
                url_hash=normalised["url_hash"],
                full_text=normalised.get("full_text"),
                summary=normalised.get("summary"),
                source_name=normalised["source_name"],
                language=normalised["language"],
                region=normalised.get("region", "algeria"),
                category=normalised.get("category", "general"),
                published_at=normalised.get("published_at"),
            )
            session.add(article)
            session.flush()  # article.id becomes available immediately
            saved_ids.append(article.id)

        session.commit()
    return saved_ids


def _pick_first(data: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _parse_published(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        pass

    try:
        return parsedate_to_datetime(cleaned)
    except (TypeError, ValueError):
        return None


def _normalise_article_payload(data: dict[str, Any]) -> dict[str, Any] | None:
    url = _pick_first(data, ["url"])
    url_hash = _pick_first(data, ["url_hash"])
    if not url or not url_hash:
        return None

    title = _pick_first(data, ["title", "title_norm", "title_raw"]) or f"Untitled article: {url[:80]}"
    summary = _pick_first(data, ["summary", "summary_norm", "summary_raw"])
    full_text = _pick_first(data, ["full_text"])

    return {
        "title": str(title),
        "url": str(url),
        "url_hash": str(url_hash),
        "summary": str(summary) if summary is not None else None,
        "full_text": str(full_text) if full_text is not None else None,
        "source_name": str(_pick_first(data, ["source_name"]) or "Unknown"),
        "language": str(_pick_first(data, ["language"]) or "unknown"),
        "region": str(_pick_first(data, ["region"]) or "algeria"),
        "category": str(_pick_first(data, ["category"]) or "general"),
        "published_at": _parse_published(_pick_first(data, ["published_at", "published"])),
    }


def _append_note(notes: str, note: str) -> str:
    return f"{notes}; {note}" if notes else note


def _write_log(run_at, found, dupes, new, groups_created, status, notes):
    """Write a CollectionLog entry."""
    with get_db_session() as session:
        log = CollectionLog(
            run_at=run_at,
            articles_found=found,
            duplicates=dupes,
            new_stories=new,
            groups_created=groups_created,
            status=status,
            notes=notes,
        )
        session.add(log)
        session.commit()
