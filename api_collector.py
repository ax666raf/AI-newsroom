# =============================================================================
# api_collector.py — Amani's News API Collector
# Collects English Algeria news from NewsAPI.org and The Guardian API
# =============================================================================

import requests
import logging
from datetime import datetime, timedelta, timezone

from sources import NEWSAPI_CONFIG, GUARDIAN_CONFIG, ALGERIA_KEYWORDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [API] %(message)s")
log = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc)


# ── KEYWORD FILTER ────────────────────────────────────────────────────────────

def contains_algeria(text: str) -> bool:
    text_lower = (text or "").lower()
    return any(kw in text_lower for kw in ALGERIA_KEYWORDS)

def is_algeria_relevant(title: str, body: str) -> bool:
    return contains_algeria(title) or contains_algeria(body)


# ── NEWSAPI.ORG ───────────────────────────────────────────────────────────────

def collect_from_newsapi() -> list:
    articles = []
    cfg = NEWSAPI_CONFIG

    if not cfg["api_key"]:
        log.warning("NewsAPI key not set — skipping.")
        return []

    log.info(f"NewsAPI key loaded: {cfg['api_key'][:8]}...")

    # Free plan limitation: can only search articles up to 1 month old
    # Using 7 days to be safe and get more results
    from_date = (utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")

    params = {
        "q":        cfg["query"],
        "language": cfg["language"],
        "sortBy":   cfg["sort_by"],
        "pageSize": cfg["page_size"],
        "from":     from_date,
        "apiKey":   cfg["api_key"],
    }

    log.info(f"Querying NewsAPI: q='{cfg['query']}' from={from_date}")

    try:
        response = requests.get(cfg["base_url"], params=params, timeout=15)
        log.info(f"  Response status: {response.status_code}")
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            log.error(f"  NewsAPI error: {data.get('message')} (code: {data.get('code')})")
            return []

        total = data.get("totalResults", 0)
        log.info(f"  NewsAPI reports {total} total results")

        for item in data.get("articles", []):
            title  = item.get("title", "") or ""
            body   = item.get("content", "") or item.get("description", "") or ""
            url    = item.get("url", "")
            source = item.get("source", {}).get("name", "NewsAPI")
            pub_at = item.get("publishedAt", utcnow().isoformat())

            if not url or "[Removed]" in title:
                continue

            if not is_algeria_relevant(title, body):
                continue

            articles.append({
                "headline":     title.strip(),
                "url":          url.strip(),
                "source_name":  source,
                "published_at": pub_at,
                "full_text":    body.strip(),
                "language":     "en",
                "collected_by": "newsapi",
            })

        log.info(f"  ✓ {len(articles)} Algeria-relevant articles from NewsAPI")

    except requests.exceptions.HTTPError as e:
        log.error(f"  ✗ NewsAPI HTTP error: {e} — Response: {e.response.text[:300]}")
    except requests.exceptions.RequestException as e:
        log.error(f"  ✗ NewsAPI request failed: {e}")

    return articles


# ── THE GUARDIAN API ──────────────────────────────────────────────────────────

def collect_from_guardian() -> list:
    articles = []
    cfg = GUARDIAN_CONFIG

    if not cfg["api_key"]:
        log.warning("Guardian API key not set — skipping.")
        return []

    log.info(f"Guardian key loaded: {cfg['api_key'][:8]}...")

    from_date = (utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    params = {
        "q":            cfg["query"],
        "lang":         cfg["lang"],
        "page-size":    cfg["page_size"],
        "from-date":    from_date,
        "show-fields":  cfg["show_fields"],
        "api-key":      cfg["api_key"],
        "order-by":     "newest",
    }

    log.info(f"Querying Guardian API: q='{cfg['query']}' from={from_date}")

    try:
        response = requests.get(cfg["base_url"], params=params, timeout=15)
        log.info(f"  Response status: {response.status_code}")
        response.raise_for_status()
        data = response.json()

        results = data.get("response", {}).get("results", [])
        total   = data.get("response", {}).get("total", 0)
        log.info(f"  Guardian reports {total} total results")

        for item in results:
            fields  = item.get("fields", {})
            title   = fields.get("headline", item.get("webTitle", ""))
            body    = fields.get("bodyText", "")
            url     = item.get("webUrl", "")
            pub_at  = item.get("webPublicationDate", utcnow().isoformat())

            if not url:
                continue

            if not is_algeria_relevant(title, body):
                continue

            articles.append({
                "headline":     title.strip(),
                "url":          url.strip(),
                "source_name":  "The Guardian",
                "published_at": pub_at,
                "full_text":    body.strip(),
                "language":     "en",
                "collected_by": "guardian",
            })

        log.info(f"  ✓ {len(articles)} Algeria-relevant articles from The Guardian")

    except requests.exceptions.HTTPError as e:
        log.error(f"  ✗ Guardian HTTP error: {e} — Response: {e.response.text[:300]}")
    except requests.exceptions.RequestException as e:
        log.error(f"  ✗ Guardian request failed: {e}")

    return articles


# ── MAIN COLLECTOR ────────────────────────────────────────────────────────────

def collect_all_apis() -> list:
    all_articles = []
    all_articles.extend(collect_from_newsapi())
    all_articles.extend(collect_from_guardian())
    log.info(f"API collection complete — {len(all_articles)} total articles")
    return all_articles


if __name__ == "__main__":
    results = collect_all_apis()
    print(f"\n{'='*60}")
    print(f"Total articles from APIs: {len(results)}")
    print(f"{'='*60}")
    for a in results[:10]:
        print(f"\n  Source : {a['source_name']}")
        print(f"  Title  : {a['headline']}")
        print(f"  Date   : {a['published_at']}")
        print(f"  URL    : {a['url']}")