# ai_processing/rag_pipeline.py

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from backend.ai_processing.gemini_client import GeminiClient
from backend.ai_processing.parser import safe_process
from backend.ai_processing.prompts import build_story_group_prompt
from backend.ai_processing.retriever import get_relevant_historical_articles

from backend.database.db import get_db_session
from backend.database.models import StoryGroup, Article, CollectionLog

logger = logging.getLogger(__name__)

OUTPUT_LANGUAGES = ("ar", "fr", "en")
MAX_GROUPS = 15
TODAYS_ARTICLES_LIMIT = 20
HISTORICAL_CONTEXT_LIMIT = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_top_story_groups(session, limit: int) -> list[StoryGroup]:
    stmt = (
        select(StoryGroup)
        .order_by(StoryGroup.coverage_count.desc(), StoryGroup.updated_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def _get_todays_articles(session, group_id: int) -> list[dict[str, Any]]:
    stmt = (
        select(Article)
        .where(Article.group_id == group_id)
        .order_by(Article.collected_at.desc())
        .limit(TODAYS_ARTICLES_LIMIT)
    )

    articles = session.scalars(stmt).all()

    return [
        {
            "title": a.title,
            "summary": a.summary,
            "source": a.source_name,
            "language": a.language,
            "full_text": a.full_text,
            "published_at": a.published_at,
        }
        for a in articles
    ]


def process_single_group(session, group: StoryGroup, gemini: GeminiClient) -> bool:
    """
    Process one story group for all three output languages.

    Returns True if all language outputs were generated and stored successfully.
    Returns False if any step fails.
    """
    try:
        todays_articles = _get_todays_articles(session, group.id)
        if not todays_articles:
            logger.warning("No articles found for group=%s", group.id)
            return False

        historical_context = get_relevant_historical_articles(
            group.id,
            limit=HISTORICAL_CONTEXT_LIMIT,
        )

        results: dict[str, dict[str, Any]] = {}

        for lang in OUTPUT_LANGUAGES:
            try:
                prompt = build_story_group_prompt(
                    output_language=lang,
                    todays_articles=todays_articles,
                    historical_background=historical_context,
                )

                raw_response = gemini.generate(prompt)
                parsed = safe_process(
                    raw_response,
                    fallback_headline=group.primary_title,
                )

                results[lang] = parsed

                logger.info("AI success: group=%s lang=%s", group.id, lang)

            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "AI language failure: group=%s lang=%s error=%s",
                    group.id,
                    lang,
                    exc,
                )
                return False

        # Store multilingual StoryGroup fields
        group.neutral_title_ar = results["ar"]["neutral_headline"]
        group.summary_ar = results["ar"]["summary"]
        group.why_it_matters_ar = results["ar"]["why_it_matters"]

        group.neutral_title_fr = results["fr"]["neutral_headline"]
        group.summary_fr = results["fr"]["summary"]
        group.why_it_matters_fr = results["fr"]["why_it_matters"]

        group.neutral_title_en = results["en"]["neutral_headline"]
        group.summary_en = results["en"]["summary"]
        group.why_it_matters_en = results["en"]["why_it_matters"]

        # Shared fields: use English as canonical
        group.category = results["en"].get("category", "general")
        group.sentiment = results["en"].get("sentiment", "neutral")

        return True

    except Exception as exc:  # noqa: BLE001
        logger.exception("Group failure: group=%s error=%s", group.id, exc)
        return False


def run_full_ai_processing(limit: int = MAX_GROUPS) -> dict[str, Any]:
    """
    Run AI processing for the top-ranked story groups.

    Commits after each group so completed work is preserved.
    """
    stats = {
        "groups_selected": 0,
        "groups_success": 0,
        "groups_failed": 0,
    }

    gemini = GeminiClient()
    start_time = _now()

    with get_db_session() as session:
        groups = _get_top_story_groups(session, limit)
        stats["groups_selected"] = len(groups)

        if not groups:
            logger.info("No story groups available for AI processing")
            return stats

        for group in groups:
            try:
                success = process_single_group(session, group, gemini)

                if success:
                    stats["groups_success"] += 1
                else:
                    stats["groups_failed"] += 1

                session.commit()
                logger.info("Committed StoryGroup id=%s", group.id)

            except Exception as exc:  # noqa: BLE001
                stats["groups_failed"] += 1
                session.rollback()
                logger.exception(
                    "Fatal pipeline error on group=%s error=%s",
                    group.id,
                    exc,
                )

        status = "success"
        if stats["groups_failed"] and stats["groups_success"]:
            status = "partial"
        elif stats["groups_failed"] and not stats["groups_success"]:
            status = "failed"

        duration_seconds = int((_now() - start_time).total_seconds())
        notes = (
            f"AI processing run completed. "
            f"Selected={stats['groups_selected']}, "
            f"Success={stats['groups_success']}, "
            f"Failed={stats['groups_failed']}, "
            f"Duration={duration_seconds}s."
        )

        log = CollectionLog(
            groups_created=stats["groups_success"],
            new_stories=stats["groups_selected"],
            status=status,
            notes=notes,
        )

        session.add(log)
        session.commit()

    logger.info("AI processing pipeline finished: %s", stats)
    return stats