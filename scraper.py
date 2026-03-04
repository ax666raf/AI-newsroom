# =============================================================================
# scraper.py — Amani's Full Article Text Extractor
# Uses newspaper3k to enrich articles, with smart fallback for blocked sites
# =============================================================================

import logging
import time
import re
from newspaper import Article, ArticleException

from sources import ALGERIA_KEYWORDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SCRAPER] %(message)s")
log = logging.getLogger(__name__)


# ── HTML CLEANER ──────────────────────────────────────────────────────────────

def strip_html(text: str) -> str:
    """Remove HTML tags and decode common HTML entities."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    entities = {
        '&amp;': '&', '&lt;': '<', '&gt;': '>',
        '&quot;': '"', '&#8217;': "'", '&#8216;': "'",
        '&#8220;': '"', '&#8221;': '"', '&#8230;': '...',
        '&nbsp;': ' ', '&#160;': ' ',
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── KEYWORD FILTER ────────────────────────────────────────────────────────────

def contains_algeria(text: str) -> bool:
    text_lower = (text or "").lower()
    return any(kw in text_lower for kw in ALGERIA_KEYWORDS)


# ── ALGERIAN SOURCE NAMES (always keep, no filter needed) ─────────────────────
ALGERIAN_SOURCES = {
    "Echorouk English", "Ennahar English", "Algeria Press Service (EN)",
    "TSA Algerie English", "Algeria Today", "Algerie360 EN"
}


# ── SINGLE ARTICLE SCRAPER ────────────────────────────────────────────────────

def scrape_article(url: str):
    """
    Download and parse a single article URL using newspaper3k.
    Returns dict with full_text and headline, or None if scraping fails.
    """
    try:
        article = Article(url, language="en", request_timeout=10)
        article.download()
        article.parse()

        full_text = article.text.strip()
        headline  = article.title.strip()

        if not full_text or len(full_text) < 100:
            return None  # Too short = probably blocked or JS-rendered

        return {
            "headline":     headline,
            "full_text":    full_text,
            "authors":      article.authors,
            "publish_date": str(article.publish_date) if article.publish_date else None,
        }

    except Exception:
        return None


# ── BATCH ENRICHER ────────────────────────────────────────────────────────────

def enrich_articles(articles: list, delay: float = 1.0) -> list:
    """
    Enriches each article with full text using newspaper3k.

    Strategy:
    - Try newspaper3k scraping first
    - If it fails, clean and use the RSS summary (HTML stripped) as fallback
    - Always strip HTML from whatever text we end up with
    - Re-applies Algeria keyword filter for international sources
    """
    enriched = []
    total = len(articles)
    scraped_ok = 0
    used_summary = 0
    dropped = 0

    log.info(f"Enriching {total} articles with full text ...")

    for i, article in enumerate(articles, 1):
        url = article.get("url", "")
        log.info(f"  [{i}/{total}] {url[:70]}...")

        scraped = scrape_article(url)

        if scraped and len(scraped["full_text"]) > 200:
            # Good scrape
            article["full_text"] = scraped["full_text"]
            if scraped["headline"] and len(scraped["headline"]) > len(article.get("headline", "")):
                article["headline"] = scraped["headline"]
            if scraped.get("authors"):
                article["authors"] = scraped["authors"]
            scraped_ok += 1
            log.info(f"    OK - full text ({len(article['full_text'])} chars)")
        else:
            # Fallback: clean up the RSS summary we already have
            rss_summary = strip_html(article.get("full_text", ""))
            article["full_text"] = rss_summary
            used_summary += 1
            log.info(f"    -> RSS fallback ({len(rss_summary)} chars)")

        # Always clean HTML from headline
        article["headline"] = strip_html(article.get("headline", ""))

        # Re-check Algeria relevance — skip filter for Algerian sources
        if article.get("source_name") not in ALGERIAN_SOURCES:
            combined = article["headline"] + " " + article["full_text"]
            if not contains_algeria(combined):
                log.info(f"    -> Dropped (not Algeria-relevant)")
                dropped += 1
                continue

        enriched.append(article)

        if i < total:
            time.sleep(delay)

    log.info(f"Enrichment done — scraped: {scraped_ok}, fallback: {used_summary}, dropped: {dropped}, kept: {len(enriched)}/{total}")
    return enriched


if __name__ == "__main__":
    test_url = "https://www.algerie360.com/meteo-algerie-la-neige-fait-son-retour-ce-mercredi-4-mars-voici-les-regions-concernees/"
    print(f"Testing scraper on: {test_url}")
    result = scrape_article(test_url)
    if result:
        print(f"  Headline : {result['headline']}")
        print(f"  Text     : {result['full_text'][:300]}...")
    else:
        print("  Scraping failed — site likely blocks newspaper3k")