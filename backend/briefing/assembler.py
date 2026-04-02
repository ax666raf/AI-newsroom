"""assembler.py - Build and persist daily newsroom briefings."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, select

from backend.database.db import get_db_session
from backend.database.models import Article, Briefing, StoryGroup

logger = logging.getLogger(__name__)

BRIEFING_CATEGORIES = (
    "Politics",
    "Economy",
    "Society",
    "Security",
    "Energy",
    "Sports",
    "World",
)


def _day_bounds_utc(now: datetime | None = None) -> tuple[datetime, datetime]:
    current = now or datetime.now(timezone.utc)
    start = datetime(current.year, current.month, current.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _bucket_category(value: str | None) -> str:
    text = (value or "").strip().lower()
    if any(k in text for k in ("politic", "government", "election", "diploma")):
        return "Politics"
    if any(k in text for k in ("econom", "business", "finance", "market", "trade")):
        return "Economy"
    if any(k in text for k in ("society", "health", "culture", "education", "social")):
        return "Society"
    if any(k in text for k in ("security", "defense", "military", "terror", "crime")):
        return "Security"
    if any(k in text for k in ("energy", "oil", "gas", "power", "electric")):
        return "Energy"
    if any(k in text for k in ("sport", "football", "athlet", "match")):
        return "Sports"
    return "World"


def _importance_score(group: StoryGroup, now: datetime) -> float:
    coverage = float(group.coverage_count or 0)
    source_count = float(len(set(group.source_names or [])))

    updated = group.updated_at or now
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)

    age_hours = max(0.0, (now - updated).total_seconds() / 3600.0)
    freshness = max(0.0, (48.0 - age_hours) / 48.0) * 5.0

    return round((coverage * 2.0) + (source_count * 1.5) + freshness, 4)


def _latest_language_article(
    session,
    group_id: int,
    language: str,
) -> dict[str, Any] | None:
    stmt = (
        select(Article.title, Article.summary)
        .where(Article.group_id == group_id)
        .where(Article.language == language)
        .where(Article.summary.isnot(None))
        .order_by(Article.collected_at.desc())
        .limit(1)
    )
    row = session.execute(stmt).first()
    if not row:
        return None

    summary = (row.summary or "").strip()
    if not summary:
        return None

    return {
        "title": (row.title or "").strip(),
        "summary": summary,
    }


def _query_today_ai_processed_groups(session, start: datetime, end: datetime) -> list[StoryGroup]:
    stmt = (
        select(StoryGroup)
        .where(StoryGroup.updated_at >= start)
        .where(StoryGroup.updated_at < end)
        .where(and_(StoryGroup.summary.isnot(None), StoryGroup.neutral_title.isnot(None)))
        .order_by(StoryGroup.coverage_count.desc(), StoryGroup.updated_at.desc())
    )
    return list(session.scalars(stmt))


def build_today_briefing_payload(language: str = "en") -> dict[str, Any]:
    """Assemble today's AI-processed stories into a categorized JSON briefing."""
    now = datetime.now(timezone.utc)
    start, end = _day_bounds_utc(now)

    with get_db_session() as session:
        groups = _query_today_ai_processed_groups(session, start, end)

        categorized: dict[str, list[dict[str, Any]]] = {name: [] for name in BRIEFING_CATEGORIES}

        for group in groups:
            score = _importance_score(group, now)
            bucket = _bucket_category(group.category)

            localized = _latest_language_article(session, group.id, language)
            headline = group.neutral_title or group.primary_title
            summary = group.summary or ""
            if localized is not None:
                headline = localized.get("title") or headline
                summary = localized.get("summary") or summary

            story = {
                "story_group_id": group.id,
                "headline": headline,
                "summary": summary,
                "why_it_matters": group.why_it_matters or "",
                "category": bucket,
                "importance_score": score,
                "coverage_count": group.coverage_count or 0,
                "source_count": len(set(group.source_names or [])),
                "sources": list(group.source_names or []),
                "languages": list(group.languages or []),
                "updated_at": group.updated_at.isoformat() if group.updated_at else None,
            }
            categorized[bucket].append(story)

    for stories in categorized.values():
        stories.sort(key=lambda item: float(item.get("importance_score", 0.0)), reverse=True)

    category_counts = {category: len(categorized[category]) for category in BRIEFING_CATEGORIES}
    total_stories = sum(category_counts.values())

    return {
        "date": start.date().isoformat(),
        "language": language,
        "total_stories": total_stories,
        "total_categories": sum(1 for count in category_counts.values() if count > 0),
        "category_counts": category_counts,
        "stories_by_category": [
            {"category": category, "stories": categorized[category]}
            for category in BRIEFING_CATEGORIES
        ],
    }


def save_today_briefing(language: str = "en") -> dict[str, Any]:
    """Build and upsert today's briefing payload into the briefings table."""
    payload = build_today_briefing_payload(language=language)
    briefing_date = datetime.fromisoformat(payload["date"]).date()

    with get_db_session() as session:
        existing = session.execute(
            select(Briefing)
            .where(Briefing.briefing_date == briefing_date)
            .where(Briefing.language == language)
            .limit(1)
        ).scalar_one_or_none()

        if existing is None:
            existing = Briefing(
                briefing_date=briefing_date,
                language=language,
                payload=payload,
                total_stories=int(payload.get("total_stories", 0)),
            )
            session.add(existing)
        else:
            existing.payload = payload
            existing.total_stories = int(payload.get("total_stories", 0))

        session.commit()

    logger.info(
        "Saved briefing: date=%s language=%s total_stories=%d",
        payload["date"],
        language,
        int(payload.get("total_stories", 0)),
    )
    return payload


def get_or_create_today_briefing(language: str = "en") -> dict[str, Any]:
    """Return today's briefing for language; assemble/save it if missing."""
    start, _ = _day_bounds_utc()
    today = start.date()

    with get_db_session() as session:
        existing = session.execute(
            select(Briefing)
            .where(Briefing.briefing_date == today)
            .where(Briefing.language == language)
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            return dict(existing.payload or {})

    return save_today_briefing(language=language)
