"""
api_collector.py — Collects Algeria-related articles via NewsAPI.org.

NewsAPI is used as a SUPPLEMENT to RSS feeds.
It lets us query by keyword + language and catches stories from
sources that do not publish RSS feeds.

Requires NEWSAPI_KEY in environment / config.

Docs: https://newsapi.org/docs/endpoints/everything
"""

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

from backend.config import NEWSAPI_KEY

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2/everything"

# Words that must appear in results so we only get Algerian stories
ALGERIA_KEYWORDS = [
    "Algeria", "Algérie", "الجزائر",
    "Algiers", "Alger", "الجزائر العاصمة",
]

# Language codes NewsAPI accepts
NEWSAPI_LANGUAGES = {"ar", "fr", "en"}


def _hash_url(url: str) -> str:
    return hashlib.md5(url.strip().lower().encode(), usedforsecurity=False).hexdigest()


def _build_query(language: str) -> str:
    """
    Build a NewsAPI `q` parameter string for Algeria in the given language.
    """
    if language == "ar":
        return 'الجزائر OR "الجزائر العاصمة"'
    if language == "fr":
        return 'Algérie OR "Alger" OR "DZ"'
    return 'Algeria OR Algiers'


def fetch_newsapi(language: str, days_back: int = 1) -> list[dict]:
    """
    Fetch recent Algeria articles from NewsAPI for one language.

    Args:
        language : "ar" | "fr" | "en"
        days_back: how many days back to search (default 1 = yesterday+today)

    Returns:
        list of raw article dicts compatible with rss_collector output.
    """
    if not NEWSAPI_KEY:
        logger.warning("NEWSAPI_KEY not set — skipping API collection for %s", language)
        return []

    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "q": _build_query(language),
        "language": language,
        "from": from_date,
        "sortBy": "publishedAt",
        "pageSize": 100,
        "apiKey": NEWSAPI_KEY,
    }

    try:
        response = requests.get(NEWSAPI_BASE, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.error("NewsAPI request failed (%s): %s", language, exc)
        return []

    articles = []
    for item in data.get("articles", []):
        url = (item.get("url") or "").strip()
        if not url or url == "https://removed.com":
            continue

        published_raw = item.get("publishedAt")
        try:
            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00")) if published_raw else None
        except ValueError:
            published_at = None

        articles.append({
            "title":        (item.get("title") or "").strip(),
            "url":          url,
            "url_hash":     _hash_url(url),
            "summary":      (item.get("description") or "")[: 1000],
            "full_text":    (item.get("content") or ""),
            "source_name":  (item.get("source", {}) or {}).get("name", "Unknown"),
            "language":     language,
            "region":       "algeria",
            "category":     "general",
            "published_at": published_at,
            "collected_at": datetime.now(timezone.utc),
        })

    logger.info("NewsAPI [%s] → %d articles", language, len(articles))
    return articles


def fetch_all_newsapi() -> list[dict]:
    """Fetch from NewsAPI across all 3 languages."""
    results = []
    for lang in ("ar", "fr", "en"):
        results.extend(fetch_newsapi(lang))
    return results

