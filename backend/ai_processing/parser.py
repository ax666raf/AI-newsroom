"""parser.py - Safe parsing and normalization of Gemini JSON responses."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = (
    "neutral_headline",
    "summary",
    "why_it_matters",
    "category",
    "sentiment",
    "context_used",
)

VALID_CATEGORIES = {
    "World",
    "Politics",
    "Economy",
    "Business",
    "Technology",
    "Science",
    "Health",
    "Sports",
    "Culture",
}

VALID_SENTIMENTS = {"positive", "neutral", "negative", "mixed"}

CATEGORY_ALIASES = {
    "general": "World",
    "international": "World",
    "world": "World",
    "politics": "Politics",
    "government": "Politics",
    "economy": "Economy",
    "economic": "Economy",
    "business": "Business",
    "technology": "Technology",
    "tech": "Technology",
    "science": "Science",
    "health": "Health",
    "sports": "Sports",
    "sport": "Sports",
    "culture": "Culture",
}

SENTIMENT_ALIASES = {
    "positive": "positive",
    "neutral": "neutral",
    "negative": "negative",
    "mixed": "mixed",
    "balanced": "neutral",
    "unknown": "neutral",
}


def minimal_valid_briefing() -> dict[str, Any]:
    """Return a guaranteed-valid fallback payload."""
    return {
        "neutral_headline": "News update",
        "summary": "No reliable summary was generated.",
        "why_it_matters": "Additional context is currently unavailable.",
        "category": "World",
        "sentiment": "neutral",
        "context_used": False,
    }


def strip_markdown_fences(raw_response: str | None) -> str:
    """Strip markdown fences while preserving inner JSON text."""
    text = (raw_response or "").strip()
    if not text:
        return ""

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _parse_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _extract_json_object_with_regex(text: str) -> str | None:
    """Fallback search for a JSON object inside mixed model output."""
    if not text:
        return None

    greedy_match = re.search(r"\{[\s\S]*\}", text)
    if greedy_match:
        return greedy_match.group(0)

    return None


def _normalize_text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _normalize_category(value: Any) -> str:
    if not isinstance(value, str):
        return "World"

    cleaned = value.strip()
    if not cleaned:
        return "World"

    alias = CATEGORY_ALIASES.get(cleaned.lower())
    if alias:
        return alias

    if cleaned in VALID_CATEGORIES:
        return cleaned

    candidate = cleaned.title()
    if candidate in VALID_CATEGORIES:
        return candidate

    return "World"


def _normalize_sentiment(value: Any) -> str:
    if not isinstance(value, str):
        return "neutral"

    cleaned = value.strip().lower()
    if not cleaned:
        return "neutral"

    return SENTIMENT_ALIASES.get(cleaned, "neutral")


def _normalize_context_used(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1", "used", "y"}:
            return True
        if lowered in {"false", "no", "0", "not_used", "n"}:
            return False
    return False


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    base = minimal_valid_briefing()

    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        logger.warning("Gemini response missing required fields: %s", ", ".join(missing))

    merged = {**base, **{k: v for k, v in payload.items() if k in REQUIRED_FIELDS}}

    return {
        "neutral_headline": _normalize_text(merged.get("neutral_headline"), base["neutral_headline"]),
        "summary": _normalize_text(merged.get("summary"), base["summary"]),
        "why_it_matters": _normalize_text(merged.get("why_it_matters"), base["why_it_matters"]),
        "category": _normalize_category(merged.get("category")),
        "sentiment": _normalize_sentiment(merged.get("sentiment")),
        "context_used": _normalize_context_used(merged.get("context_used")),
    }


def parse_gemini_response(raw_response: str | None) -> dict[str, Any]:
    """
    Parse raw Gemini output into a guaranteed-valid briefing payload.

    Behavior:
      1) Strip markdown fences.
      2) Parse JSON directly.
      3) Fallback: regex extract JSON object and parse again.
      4) Validate/normalize required fields and safe defaults.
      5) Never raise; always return a valid payload.
    """
    cleaned = strip_markdown_fences(raw_response)

    payload = _parse_json_object(cleaned)
    if payload is None:
        candidate = _extract_json_object_with_regex(cleaned)
        if candidate is not None:
            payload = _parse_json_object(candidate)

    if payload is None:
        logger.warning("Failed to parse Gemini response as JSON; using minimal fallback")
        return minimal_valid_briefing()

    try:
        return _normalize_payload(payload)
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected parser failure; returning minimal fallback")
        return minimal_valid_briefing()
