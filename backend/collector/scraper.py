import logging
from datetime import datetime
from urllib.parse import urlparse
from newspaper import Article, Config

try:
    from backend.collector.apify_collector import apify_scrape, needs_apify
except ImportError:
    from collector.apify_collector import apify_scrape, needs_apify

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _build_config(language="fr"):
    cfg = Config()
    cfg.browser_user_agent = USER_AGENT
    cfg.request_timeout = 15
    cfg.language = language
    cfg.fetch_images = False
    cfg.memoize_articles = False
    return cfg


def scrape_article(url, language="fr"):
    if needs_apify(url):
        logger.info(f"known blocked domain, going straight to apify for {url}")
        result = _try_apify(url)
        if result:
            return result

    result = _try_newspaper(url, language)
    if result and result.get("full_text") and len(result["full_text"]) > 150:
        return result

    logger.info(f"newspaper3k failed or too short for {url}, trying apify")
    result = _try_apify(url)
    if result:
        return result

    logger.warning(f"all extraction methods failed for {url}")
    return None


def _try_newspaper(url, language):
    try:
        cfg = _build_config(language)
        article = Article(url, config=cfg)
        article.download()
        article.parse()

        return {
            "title": article.title,
            "url": url,
            "full_text": article.text,
            "authors": article.authors,
            "published_at": article.publish_date,
            "source_name": _extract_domain(url),
            "language": language,
            "collected_at": datetime.utcnow(),
        }
    except Exception as e:
        logger.debug(f"newspaper3k error for {url}: {e}")
        return None


def _try_apify(url):
    try:
        data = apify_scrape(url)
        if not data or not data.get("text"):
            return None
        return {
            "title": data.get("title", ""),
            "url": url,
            "full_text": data.get("text", ""),
            "authors": [],
            "published_at": data.get("published_at"),
            "source_name": data.get("source_name", _extract_domain(url)),
            "language": data.get("language", _detect_lang(data.get("text", ""))),
            "collected_at": datetime.utcnow(),
        }
    except Exception as e:
        logger.debug(f"apify fallback error for {url}: {e}")
        return None


def _detect_lang(text):
    if not text or len(text) < 30:
        return "fr"
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return "fr"


def _extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    return domain


def scrape_multiple(urls, language="fr"):
    results = []
    for url in urls:
        article = scrape_article(url, language)
        if article:
            results.append(article)
    return results


def enrich_articles(articles: list[dict]) -> list[dict]:
    """
    Enrich articles by scraping full text for those missing it.
    
    Takes a list of article dicts (typically from RSS/API collectors)
    and attempts to scrape full text content for articles that don't
    already have it.  Returns the enriched articles.
    
    Articles that fail scraping are returned as-is (with whatever
    summary/text they already had).
    
    Args:
        articles: List of article dicts (must have 'url', 'language').
    
    Returns:
        List of enriched article dicts with full_text populated where possible.
    """
    logger.info("Starting article enrichment (%d articles)", len(articles))
    enriched = []
    scraped_count = 0
    
    for article in articles:
        url = article.get("url")
        language = article.get("language", "fr")
        
        # Skip if already has substantial full_text
        existing_text = article.get("full_text", "")
        if existing_text and len(existing_text) > 200:
            enriched.append(article)
            continue
        
        # Try to scrape
        if url:
            scraped = scrape_article(url, language)
            if scraped and scraped.get("full_text"):
                # Merge scraped data into article
                article["full_text"] = scraped.get("full_text")
                article["authors"] = scraped.get("authors", [])
                if scraped.get("published_at"):
                    article["published_at"] = scraped.get("published_at")
                scraped_count += 1
                logger.debug(f"Scraped full text for {url}")
        
        enriched.append(article)
    
    logger.info("Article enrichment complete: %d articles scraped", scraped_count)
    return enriched
