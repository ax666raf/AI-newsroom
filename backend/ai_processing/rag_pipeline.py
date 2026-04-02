"""rag_pipeline.py - Orchestrates multilingual RAG briefing generation."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update

from backend.ai_processing.gemini_client import GeminiClient
from backend.ai_processing.parser import parse_gemini_response
from backend.ai_processing.prompts import build_story_group_prompt
from backend.ai_processing.retriever import get_relevant_historical_articles
from backend.database.db import get_db_session
from backend.database.models import Article, StoryGroup

logger = logging.getLogger(__name__)

OUTPUT_LANGUAGES = ("ar", "fr", "en")
MAX_GROUPS_PER_RUN = 15
TODAYS_ARTICLES_LIMIT = 20
HISTORICAL_CONTEXT_LIMIT = 5


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ranked_story_group_ids(session, limit: int) -> list[int]:
    """
    Rank groups by coverage and freshness, then return top IDs.

    Ranking proxy:
      1) Highest coverage_count
      2) Most recently updated
    """
    effective_limit = max(0, min(limit, MAX_GROUPS_PER_RUN))
    if effective_limit == 0:
        return []

    stmt = (
        select(StoryGroup.id)
        .order_by(StoryGroup.coverage_count.desc(), StoryGroup.updated_at.desc())
        .limit(effective_limit)
    )
    return [int(row[0]) for row in session.execute(stmt)]


def _load_todays_group_articles(
    session,
    group_id: int,
    now: datetime,
    lookback_hours: int = 36,
) -> list[dict[str, Any]]:
    window_start = now - timedelta(hours=lookback_hours)

    stmt = (
        select(
            Article.id,
            Article.title,
            Article.full_text,
            Article.summary,
            Article.source_name,
            Article.language,
            Article.published_at,
            Article.collected_at,
            Article.url,
        )
        .where(Article.group_id == group_id)
        .where(Article.collected_at >= window_start)
        .order_by(Article.collected_at.desc())
        .limit(TODAYS_ARTICLES_LIMIT)
    )

    rows = session.execute(stmt).all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "full_text": row.full_text,
            "summary": row.summary,
            "source_name": row.source_name,
            "language": row.language,
            "published_at": row.published_at,
            "collected_at": row.collected_at,
            "url": row.url,
        }
        for row in rows
    ]


def _persist_language_results_on_articles(
    session,
    group_id: int,
    language_results: dict[str, dict[str, Any]],
) -> None:
    """Store generated per-language summary/category on grouped articles."""
    for language, result in language_results.items():
        stmt = (
            update(Article)
            .where(Article.group_id == group_id)
            .where(Article.language == language)
            .values(
                summary=str(result.get("summary") or ""),
                category=str(result.get("category") or "general"),
            )
        )
        session.execute(stmt)


def _pick_canonical_result(language_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if "en" in language_results:
        return language_results["en"]
    if language_results:
        first_key = next(iter(language_results))
        return language_results[first_key]
    return parse_gemini_response(None)


def run_rag_pipeline(max_groups: int = MAX_GROUPS_PER_RUN) -> dict[str, Any]:
    """
    Run multilingual RAG generation for top-ranked story groups.

    Flow per group:
      retrieve context -> build prompt -> Gemini call -> parse response -> store -> commit

    Commits after each group (not at end) so partial progress is preserved.
    """
    stats = {
        "groups_selected": 0,
        "groups_processed": 0,
        "groups_failed": 0,
        "language_successes": 0,
        "language_failures": 0,
    }

    gemini = GeminiClient()
    now = _now_utc()

    with get_db_session() as session:
        group_ids = _ranked_story_group_ids(session, max_groups)
        stats["groups_selected"] = len(group_ids)

    if not group_ids:
        logger.info("RAG pipeline: no story groups selected")
        return stats

    for group_id in group_ids:
        try:
            with get_db_session() as session:
                group = session.get(StoryGroup, group_id)
                if group is None:
                    stats["groups_failed"] += 1
                    logger.warning("RAG pipeline: StoryGroup %d not found", group_id)
                    continue

                todays_articles = _load_todays_group_articles(session, group_id, now)
                historical_context = get_relevant_historical_articles(
                    group_id,
                    limit=HISTORICAL_CONTEXT_LIMIT,
                )

                language_results: dict[str, dict[str, Any]] = {}

                for output_language in OUTPUT_LANGUAGES:
                    try:
                        prompt = build_story_group_prompt(
                            output_language=output_language,
                            todays_articles=todays_articles,
                            historical_background=historical_context,
                        )
                        raw = gemini.generate(prompt)
                        parsed = parse_gemini_response(raw)
                        language_results[output_language] = parsed
                        stats["language_successes"] += 1
                        logger.info(
                            "RAG pipeline success: group=%d language=%s",
                            group_id,
                            output_language,
                        )
                    except Exception as exc:  # noqa: BLE001
                        stats["language_failures"] += 1
                        language_results[output_language] = parse_gemini_response(None)
                        logger.exception(
                            "RAG pipeline failure: group=%d language=%s error=%s",
                            group_id,
                            output_language,
                            exc,
                        )

                _persist_language_results_on_articles(session, group_id, language_results)

                canonical = _pick_canonical_result(language_results)
                group.neutral_title = str(canonical.get("neutral_headline") or group.primary_title)
                group.summary = str(canonical.get("summary") or "")
                group.why_it_matters = str(canonical.get("why_it_matters") or "")
                group.category = str(canonical.get("category") or "World")

                # Persist progress immediately per group.
                session.commit()

                stats["groups_processed"] += 1
                logger.info("RAG pipeline committed group %d", group_id)

        except Exception as exc:  # noqa: BLE001
            stats["groups_failed"] += 1
            logger.exception("RAG pipeline group-level failure: group=%d error=%s", group_id, exc)

    logger.info("RAG pipeline finished: %s", stats)
    return stats
