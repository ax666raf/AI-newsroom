# =============================================================================
# main_collector.py — Amani's Main Pipeline Runner
# Runs all collectors in sequence and outputs a clean JSON file
# Run this file every day at 5:00 AM via scheduler
# =============================================================================

import json
import logging
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc)

from rss_collector import collect_all_rss
from api_collector import collect_all_apis
from scraper import enrich_articles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MAIN] %(message)s")
log = logging.getLogger(__name__)


def deduplicate_by_url(articles: list[dict]) -> list[dict]:
    """Quick deduplication by URL before passing to full dedup pipeline."""
    seen_urls = set()
    unique = []
    for a in articles:
        url = a.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(a)
    return unique


def run_english_collection() -> list[dict]:
    """
    Full English collection pipeline:
    1. RSS feeds
    2. News APIs (NewsAPI + Guardian)
    3. Scrape full text
    4. Basic URL deduplication
    5. Save to JSON
    """
    log.info("=" * 60)
    log.info("AMANI — English Algeria News Collection Starting")
    log.info(f"Time: {utcnow().isoformat()}")
    log.info("=" * 60)

    # ── Step 1: Collect from RSS ──
    log.info("\n[Step 1] Collecting from RSS feeds ...")
    rss_articles = collect_all_rss()

    # ── Step 2: Collect from APIs ──
    log.info("\n[Step 2] Collecting from News APIs ...")
    api_articles = collect_all_apis()

    # ── Step 3: Combine ──
    all_articles = rss_articles + api_articles
    log.info(f"\n[Step 3] Combined total: {len(all_articles)} articles")

    # ── Step 4: Remove URL duplicates (quick pre-filter) ──
    all_articles = deduplicate_by_url(all_articles)
    log.info(f"         After URL dedup: {len(all_articles)} articles")

    # ── Step 5: Enrich with full text ──
    log.info("\n[Step 4] Enriching with full article text ...")
    all_articles = enrich_articles(all_articles, delay=1.5)

    # ── Step 6: Save results ──
    today = utcnow().strftime("%Y-%m-%d")
    output_path = f"english_articles_{today}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    log.info(f"\n{'='*60}")
    log.info(f"✅ Collection complete!")
    log.info(f"   Total articles: {len(all_articles)}")
    log.info(f"   Saved to: {output_path}")
    log.info(f"{'='*60}")

    return all_articles


if __name__ == "__main__":
    articles = run_english_collection()

    # Print a summary preview
    print(f"\n📰 TODAY'S ENGLISH ALGERIA NEWS — {len(articles)} articles\n")
    for i, a in enumerate(articles[:10], 1):
        print(f"  {i:02}. [{a['collected_by'].upper()}] {a['headline'][:70]}")
        print(f"      Source: {a['source_name']} | Date: {a['published_at'][:10]}")
        print()