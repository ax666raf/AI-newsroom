"""
rss_collector.py — Fetches and parses RSS/Atom feeds from SOURCES.

Flow per source:
  1. GET the RSS URL with a short timeout
  2. Parse with feedparser
  3. For each entry: extract title, url, summary, published_date
  4. Normalise Arabic text if language == "ar"
  5. Return list[dict]  (raw articles, not yet saved to DB)
"""

import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests

from .sources import get_rss_sources
from .arabic_normalizer import normalize_arabic

logger = logging.getLogger(__name__)

# How long to wait for a single RSS feed (seconds)
RSS_TIMEOUT = 10


def _parse_date(entry) -> Optional[datetime]:
    """Convert feedparser's time struct to a timezone-aware datetime."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return None


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()


def _clean_html(text: str) -> str:
    """Strip basic HTML tags from summary snippets."""
    import re
    return re.sub(r"<[^>]+>", "", text or "").strip()


def fetch_rss_source(source: dict) -> list[dict]:
    """
    Fetch and parse a single RSS source.

    Returns a list of raw article dicts:
      {title, url, url_hash, summary, source_name,
       language, published_at, collected_at, region}
    """
    articles = []
    rss_url = source["rss"]
    lang = source["language"]

    try:
        # feedparser can use requests; supply timeout via User-Agent header trick
        response = requests.get(rss_url, timeout=RSS_TIMEOUT, headers={
            "User-Agent": "AlgeriaNewsBot/1.0 (+https://github.com/your-org/AI-newsroom)"
        })
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.RequestException as exc:
        logger.warning("RSS fetch failed for %s: %s", source["name"], exc)
        return []

    if feed.bozo and not feed.entries:
        logger.warning("Could not parse RSS for %s (bozo flag)", source["name"])
        return []

    for entry in feed.entries:
        url = entry.get("link", "").strip()
        if not url:
            continue

        title = entry.get("title", "").strip()
        summary = _clean_html(entry.get("summary", entry.get("description", "")))

        # Arabic normalisation
        if lang == "ar":
            title = normalize_arabic(title)
            summary = normalize_arabic(summary)

        articles.append({
            "title": title,
            "url": url,
            "url_hash": _hash_url(url),
            "summary": summary[:1000],          # cap at 1 000 chars
            "full_text": None,                   # filled by scraper later
            "source_name": source["name"],
            "language": lang,
            "region": "algeria",
            "category": source.get("category", "general"),
            "published_at": _parse_date(entry),
            "collected_at": datetime.now(timezone.utc),
        })

    logger.info("RSS %s → %d articles", source["name"], len(articles))
    return articles


def fetch_all_rss() -> list[dict]:
    """
    Iterate over every RSS-enabled source and collect articles.
    Returns a flat deduplicated list (by URL hash).
    """
    seen_hashes: set[str] = set()
    all_articles: list[dict] = []

    for source in get_rss_sources():
        for article in fetch_rss_source(source):
            h = article["url_hash"]
            if h not in seen_hashes:
                seen_hashes.add(h)
                all_articles.append(article)

    logger.info("Total RSS articles collected: %d (unique)", len(all_articles))
    return all_articles
