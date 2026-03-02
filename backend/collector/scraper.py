"""
scraper.py — Full-text article scraper (fallback / enrichment).

When RSS gives only a title + short summary, this module
visits the article URL and extracts the full body text.

Uses `newspaper3k` (newspaper library) which:
  • Works for Arabic, French, and English
  • Handles encoding automatically
  • Extracts publish date, author, and main image URL

This is intentionally slow and runs AFTER initial collection so
we only scrape articles that survive deduplication.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

try:
    from newspaper import Article as NewspaperArticle
    from newspaper import ArticleException
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Polite delay between requests (seconds)
SCRAPE_DELAY = 1.5

# Maximum characters to keep from full text
MAX_FULL_TEXT = 8000


def scrape_article(url: str, language: str = "en") -> Optional[dict]:
    """
    Fetch and parse the full text of one article URL.

    Returns a dict with enrichment fields, or None on failure:
      {full_text, published_at, top_image}
    """
    if not NEWSPAPER_AVAILABLE:
        logger.warning("newspaper3k not installed — scraping disabled")
        return None

    # Map language codes to newspaper's language param
    lang_map = {"ar": "ar", "fr": "fr", "en": "en"}
    nlp_lang = lang_map.get(language, "en")

    try:
        article = NewspaperArticle(url, language=nlp_lang, request_timeout=10)
        article.download()
        article.parse()
    except ArticleException as exc:
        logger.debug("Scrape failed for %s: %s", url, exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("Unexpected scrape error for %s: %s", url, exc)
        return None

    full_text = (article.text or "").strip()[:MAX_FULL_TEXT]
    if not full_text:
        return None

    published_at = None
    if article.publish_date:
        try:
            published_at = article.publish_date.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    return {
        "full_text":    full_text,
        "published_at": published_at,
        "top_image":    article.top_image or None,
    }


def enrich_articles(articles: list[dict]) -> list[dict]:
    """
    For each article that has no full_text yet, attempt to scrape it.
    Modifies articles in-place and returns the list.

    Only scrapes articles missing full_text to avoid redundant work.
    """
    to_scrape = [a for a in articles if not a.get("full_text")]
    logger.info("Scraping full text for %d articles ...", len(to_scrape))

    for article in to_scrape:
        enrichment = scrape_article(article["url"], article.get("language", "en"))
        if enrichment:
            article["full_text"] = enrichment["full_text"]
            if not article.get("published_at") and enrichment["published_at"]:
                article["published_at"] = enrichment["published_at"]
        time.sleep(SCRAPE_DELAY)   # polite crawling

    return articles

