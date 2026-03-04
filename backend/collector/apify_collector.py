import logging
import time
import re
from datetime import datetime
from urllib.parse import urlparse
import requests

try:
    from backend.config import APIFY_TOKEN
except ImportError:
    from config import APIFY_TOKEN

logger = logging.getLogger(__name__)

BASE_URL = "https://api.apify.com/v2"
POLL_INTERVAL = 5
MAX_WAIT = 120

ACTORS = {
    "crawler": "apify/website-content-crawler",
    "cheerio": "apify/cheerio-scraper",
    "puppeteer": "apify/puppeteer-scraper",
}

FRENCH_BLOCKED_DOMAINS = [
    "france24.com",
    "rfi.fr",
    "tsa-algerie.com",
    "elwatan.com",
    "liberte-algerie.com",
    "lesoirdalgerie.com",
    "lequotidien-oran.com",
    "aps.dz",
]

ARABIC_BLOCKED_DOMAINS = [
    "echoroukonline.com",
    "ennaharonline.com",
    "elkhabar.com",
    "elbilad.net",
    "aps.dz",
    "aljazeera.net",
    "alarabiya.net",
    "rt.com",
    "bbc.com",
    "skynewsarabia.com",
    "alshorouk.com",
]

ARABIC_PATTERN = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')


def needs_apify(url):
    domain = _extract_domain(url)
    return domain in FRENCH_BLOCKED_DOMAINS or domain in ARABIC_BLOCKED_DOMAINS


def _extract_domain(url):
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")


def _guess_language(url, text=""):
    domain = _extract_domain(url)
    if domain in ARABIC_BLOCKED_DOMAINS:
        return "ar"
    if domain in FRENCH_BLOCKED_DOMAINS:
        return "fr"
    if text and len(text) > 20:
        arabic_chars = len(ARABIC_PATTERN.findall(text))
        if arabic_chars / len(text) > 0.3:
            return "ar"
    if text and len(text) > 30:
        try:
            from langdetect import detect
            return detect(text)
        except Exception:
            pass
    return "fr"


def _pick_actor(url):
    domain = _extract_domain(url)
    if domain in ARABIC_BLOCKED_DOMAINS:
        return ACTORS["crawler"]
    return ACTORS["crawler"]


def _build_run_input(url):
    domain = _extract_domain(url)
    base_input = {
        "startUrls": [{"url": url}],
        "maxCrawlPages": 1,
    }

    if domain in ARABIC_BLOCKED_DOMAINS:
        base_input["crawlerType"] = "playwright:firefox"
        base_input["additionalMimeTypes"] = ["text/html"]
    else:
        base_input["crawlerType"] = "cheerio"

    return base_input


def _clean_arabic_text(text):
    if not text:
        return text
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]', '', text)
    return text.strip()


def _clean_french_text(text):
    if not text:
        return text
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def apify_scrape(url):
    if not APIFY_TOKEN:
        logger.error("APIFY_TOKEN not set")
        return None

    actor = _pick_actor(url)
    run_input = _build_run_input(url)
    run = _start_run(url, actor, run_input)
    if not run:
        return None

    run_id = run.get("data", {}).get("id")
    if not run_id:
        return None

    if not _wait_for_completion(run_id):
        return None

    items = _get_results(run_id)
    if not items:
        return None

    best = max(items, key=lambda x: len(x.get("text", "")))
    raw_text = best.get("text", "")
    lang = _guess_language(url, raw_text)

    if lang == "ar":
        raw_text = _clean_arabic_text(raw_text)
    else:
        raw_text = _clean_french_text(raw_text)

    metadata = best.get("metadata", {})

    return {
        "title": metadata.get("title", "") or best.get("title", ""),
        "text": raw_text,
        "language": lang,
        "published_at": _parse_date(metadata.get("publishedAt")),
        "source_name": _extract_domain(url),
    }


def _parse_date(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _start_run(url, actor_id, run_input):
    try:
        resp = requests.post(
            f"{BASE_URL}/acts/{actor_id}/runs",
            json=run_input,
            params={"token": APIFY_TOKEN},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"failed to start apify run for {url}: {e}")
        return None


def _wait_for_completion(run_id):
    elapsed = 0
    while elapsed < MAX_WAIT:
        try:
            resp = requests.get(
                f"{BASE_URL}/actor-runs/{run_id}",
                params={"token": APIFY_TOKEN},
                timeout=10,
            )
            status = resp.json().get("data", {}).get("status")
            if status == "SUCCEEDED":
                return True
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                logger.warning(f"apify run {run_id} ended with status {status}")
                return False
        except Exception as e:
            logger.debug(f"poll error: {e}")

        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    logger.warning(f"apify run {run_id} timed out after {MAX_WAIT}s")
    return False


def _get_results(run_id):
    try:
        resp = requests.get(
            f"{BASE_URL}/actor-runs/{run_id}/dataset/items",
            params={"token": APIFY_TOKEN},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"failed to get apify results for run {run_id}: {e}")
        return None


def apify_scrape_batch(urls, stop_on_fail=False):
    results = []
    for url in urls:
        data = apify_scrape(url)
        if data:
            results.append({"url": url, **data})
        elif stop_on_fail:
            break
    return results


def apify_scrape_french(urls):
    return apify_scrape_batch(urls)


def apify_scrape_arabic(urls):
    return apify_scrape_batch(urls)
