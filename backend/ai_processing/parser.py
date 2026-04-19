"""ai_processing/parser.py - Safe parsing and normalization of Gemini JSON responses."""

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
    "Politics",
    "Economy",
    "Society",
    "Security",
    "Energy",
    "Sports",
    "World",
}

VALID_SENTIMENTS = {
    "positive",
    "neutral",
    "negative",
}

CATEGORY_ALIASES = {
    "world": "World",
    "international": "World",
    "general": "World",

    "politics": "Politics",
    "political": "Politics",
    "government": "Politics",

    "economy": "Economy",
    "economic": "Economy",
    "business": "Economy",
    "finance": "Economy",

    "society": "Society",
    "social": "Society",

    "security": "Security",
    "defense": "Security",
    "defence": "Security",
    "military": "Security",

    "energy": "Energy",
    "oil": "Energy",
    "gas": "Energy",

    "sports": "Sports",
    "sport": "Sports",
}

SENTIMENT_ALIASES = {
    "positive": "positive",
    "neutral": "neutral",
    "negative": "negative",
    "mixed": "neutral",
    "balanced": "neutral",
    "unknown": "neutral",
}


def build_minimal_valid_object(
    fallback_headline: str = "News update",
) -> dict[str, Any]:
    """
    Return a guaranteed-valid minimal object.
    Used when parsing or validation fails completely.
    """
    headline = str(fallback_headline or "").strip() or "News update"

    return {
        "neutral_headline": headline,
        "summary": "No reliable summary was generated.",
        "why_it_matters": "Additional context is currently unavailable.",
        "category": "World",
        "sentiment": "neutral",
        "context_used": False,
    }


def strip_markdown_fences(raw_response: str | None) -> str:
    """
    Remove markdown code fences while preserving inner JSON text.
    Handles fenced and loosely fenced responses.
    """
    text = (raw_response or "").strip()
    if not text:
        return ""

    fenced_match = re.search(
        r"```(?:json)?\s*([\s\S]*?)\s*```",
        text,
        flags=re.IGNORECASE,
    )
    if fenced_match:
        return fenced_match.group(1).strip()

    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)

    return text.strip()


def _parse_json_object(text: str) -> dict[str, Any] | None:
    """
    Parse text as JSON and return it only if the result is a dict.
    """
    if not text:
        return None

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def extract_json_substring(text: str) -> str | None:
    """
    Fallback: extract text from the first '{' to the last '}'.
    """
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or start >= end:
        return None

    return text[start : end + 1].strip()


def _coerce_known_alias_keys(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize slight key variations from model output into canonical keys.
    """
    normalized = dict(payload)

    if "why_it_matters" not in normalized and "whyItMatters" in normalized:
        normalized["why_it_matters"] = normalized["whyItMatters"]

    if "neutral_headline" not in normalized and "neutralHeadline" in normalized:
        normalized["neutral_headline"] = normalized["neutralHeadline"]

    if "context_used" not in normalized and "contextUsed" in normalized:
        normalized["context_used"] = normalized["contextUsed"]

    return normalized


def _normalize_text(value: Any, fallback: str) -> str:
    """
    Normalize text fields to a non-empty string.
    If Gemini returns a list, join non-empty parts.
    """
    if value is None:
        return fallback

    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return " ".join(parts) if parts else fallback

    text = str(value).strip()
    return text or fallback


def _normalize_category(value: Any) -> str:
    """
    Normalize category to the allowed project category set.
    Invalid values default to 'World'.
    """
    if not isinstance(value, str):
        return "World"

    cleaned = value.strip()
    if not cleaned:
        return "World"

    if cleaned in VALID_CATEGORIES:
        return cleaned

    alias = CATEGORY_ALIASES.get(cleaned.lower())
    if alias:
        return alias

    titled = cleaned.title()
    if titled in VALID_CATEGORIES:
        return titled

    return "World"


def _normalize_sentiment(value: Any) -> str:
    """
    Normalize sentiment to allowed values.
    Invalid values default to 'neutral'.
    """
    if not isinstance(value, str):
        return "neutral"

    cleaned = value.strip().lower()
    if not cleaned:
        return "neutral"

    if cleaned in VALID_SENTIMENTS:
        return cleaned

    return SENTIMENT_ALIASES.get(cleaned, "neutral")


def _normalize_context_used(value: Any) -> bool:
    """
    Normalize context_used to bool.
    """
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


def validate_required_fields(payload: dict[str, Any]) -> None:
    """
    Ensure all required fields are present.
    Raise ValueError if any are missing.
    """
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and normalize a Gemini JSON payload into a safe structure.
    """
    payload = _coerce_known_alias_keys(payload)
    validate_required_fields(payload)

    fallback = build_minimal_valid_object(
        fallback_headline=payload.get("neutral_headline", "News update")
    )

    return {
        "neutral_headline": _normalize_text(
            payload.get("neutral_headline"),
            fallback["neutral_headline"],
        ),
        "summary": _normalize_text(
            payload.get("summary"),
            fallback["summary"],
        ),
        "why_it_matters": _normalize_text(
            payload.get("why_it_matters"),
            fallback["why_it_matters"],
        ),
        "category": _normalize_category(payload.get("category")),
        "sentiment": _normalize_sentiment(payload.get("sentiment")),
        "context_used": _normalize_context_used(payload.get("context_used")),
    }


def parse_gemini_response(raw_response: str | None) -> dict[str, Any]:
    """
    Strict parser:
    1) Strip markdown fences.
    2) Try direct JSON parsing.
    3) Fallback: extract from first '{' to last '}' and parse again.
    4) Normalize alias keys.
    5) Validate required fields.
    6) Normalize values and safe defaults.
    Raises on failure.
    """
    cleaned = strip_markdown_fences(raw_response)

    payload = _parse_json_object(cleaned)
    if payload is not None:
        return normalize_payload(payload)

    candidate = extract_json_substring(cleaned)
    if candidate is not None:
        payload = _parse_json_object(candidate)
        if payload is not None:
            return normalize_payload(payload)

    raise ValueError("Failed to extract a valid Gemini JSON object.")


def safe_process(
    raw_response: str | None,
    fallback_headline: str = "News update",
) -> dict[str, Any]:
    """
    Safe wrapper used by the pipeline.
    Never raises; always returns a valid object.
    """
    try:
        return parse_gemini_response(raw_response)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Parser failed; returning minimal fallback. headline=%r error=%s",
            fallback_headline,
            exc,
        )
        return build_minimal_valid_object(fallback_headline=fallback_headline)