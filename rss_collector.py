# =============================================================================
# rss_collector.py — RSS Feed Collector
# Collects English news articles from RSS feeds using feedparser
# =============================================================================

import feedparser
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime

from sources import RSS_SOURCES, ALGERIA_KEYWORDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [RSS] %(message)s")
log = logging.getLogger(__name__)


# ── KEYWORD FILTER ────────────────────────────────────────────────────────────

def contains_algeria(text: str) -> bool:
    """Return True if the text mentions Algeria in any relevant form."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in ALGERIA_KEYWORDS)


def is_algeria_relevant(title: str, body: str) -> bool:
    """Check title first (fast), then body."""
    return contains_algeria(title) or contains_algeria(body)


# ── DATE PARSING ──────────────────────────────────────────────────────────────

def parse_date(entry) -> str:
    """Try multiple date fields and return ISO format string."""
    # feedparser gives us 'published' as a string
    for field in ["published", "updated", "created"]:
        raw = entry.get(field)
        if raw:
            try:
                return parsedate_to_datetime(raw).isoformat()
            except Exception:
                pass
    return datetime.utcnow().isoformat()


# ── SINGLE FEED COLLECTOR ─────────────────────────────────────────────────────

def collect_from_feed(source: dict) -> list[dict]:
    """
    Parse one RSS feed and return a list of standardized article dicts.
    - Algerian sources (always_relevant=True): no keyword filter needed
    - International sources: Algeria keyword filter applied
    """
    articles = []
    name           = source["name"]
    url            = source["url"]
    always_relevant = source.get("always_relevant", False)

    log.info(f"Fetching RSS: {name} {'[Algerian — no filter]' if always_relevant else '[filter applied]'}")

    try:
        feed = feedparser.parse(url)

        if feed.bozo and feed.entries == []:
            log.warning(f"  ⚠ Feed failed or empty: {name} — {feed.bozo_exception}")
            return []

        for entry in feed.entries:
            title   = entry.get("title", "").strip()
            link    = entry.get("link", "").strip()
            summary = entry.get("summary", "") or entry.get("description", "")

            # Skip entries with no URL
            if not link:
                continue

            # ── Algeria keyword filter — SKIP for Algerian sources ──
            if not always_relevant and not is_algeria_relevant(title, summary):
                continue

            article = {
                "headline":     title,
                "url":          link,
                "source_name":  name,
                "published_at": parse_date(entry),
                "full_text":    summary,   # will be enriched by scraper.py
                "language":     "en",
                "collected_by": "rss",
            }
            articles.append(article)

        log.info(f"  ✓ {len(articles)} articles from {name}")

    except Exception as e:
        log.error(f"  ✗ Failed to collect from {name}: {e}")

    return articles


# ── MAIN COLLECTOR ────────────────────────────────────────────────────────────

def collect_all_rss() -> list[dict]:
    """
    Run all RSS sources and return combined list of articles.
    Call this from your main pipeline.
    """
    all_articles = []

    for source in RSS_SOURCES:
        articles = collect_from_feed(source)
        all_articles.extend(articles)

    log.info(f"RSS collection complete — {len(all_articles)} total articles")
    return all_articles


# ── RUN STANDALONE ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = collect_all_rss()
    print(f"\n{'='*60}")
    print(f"Total articles collected: {len(results)}")
    print(f"{'='*60}")
    for a in results[:5]:   # preview first 5
        print(f"\n  Source : {a['source_name']}")
        print(f"  Title  : {a['headline']}")
        print(f"  Date   : {a['published_at']}")
        print(f"  URL    : {a['url']}")