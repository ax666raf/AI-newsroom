"""prompts.py - Prompt builders for newsroom briefing generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _first_500_chars(value: str | None) -> str:
    text = (value or "").strip()
    return text[:500]


def _format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if value is None:
        return "unknown"
    return str(value)


def build_story_group_prompt(
    output_language: str,
    todays_articles: list[dict[str, Any]],
    historical_background: list[dict[str, Any]],
) -> str:
    """Build a strict JSON prompt for summarizing one story group."""
    lines: list[str] = []

    # First line must explicitly state output language.
    lines.append(f"Output language: {output_language}")
    lines.append("")
    lines.append("You are an AI news editor. Use the data below to produce one balanced newsroom item.")
    lines.append("")

    lines.append("Today's articles:")
    if todays_articles:
        for idx, article in enumerate(todays_articles, start=1):
            source = article.get("source_name") or article.get("source") or "unknown"
            language = article.get("language") or "unknown"
            title = article.get("title") or ""
            snippet = _first_500_chars(article.get("full_text") or article.get("summary") or "")
            lines.append(f"{idx}. source: {source}")
            lines.append(f"   language: {language}")
            lines.append(f"   title: {title}")
            lines.append(f"   first_500_chars: {snippet}")
    else:
        lines.append("none")
    lines.append("")

    lines.append("Historical background:")
    if historical_background:
        for idx, article in enumerate(historical_background, start=1):
            date_str = _format_date(article.get("published_at") or article.get("date"))
            source = article.get("source_name") or article.get("source") or "unknown"
            title = article.get("title") or ""
            summary = article.get("summary") or ""
            lines.append(f"{idx}. date: {date_str}")
            lines.append(f"   source: {source}")
            lines.append(f"   title: {title}")
            lines.append(f"   summary: {summary}")
    else:
        lines.append("none")
    lines.append("")

    lines.append("Instructions:")
    lines.append("- Write summary using exactly three sentences.")
    lines.append("- Keep wording neutral and factual.")
    lines.append("- Use historical background only when relevant and mention whether context was used.")
    lines.append("- Choose category and sentiment from the provided evidence only.")
    lines.append("")

    lines.append("Return JSON with exactly these fields:")
    lines.append("neutral_headline, summary, why_it_matters, category, sentiment, context_used")
    lines.append("return only valid JSON, no markdown, no code fences")

    return "\n".join(lines)
