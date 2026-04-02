# RSS Collector module
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Set
import time
import logging

import feedparser

import re
from bs4 import BeautifulSoup

from backend.collector.sources import ARABIC_RSS_SOURCES, ENGLISH_RSS_SOURCES, ENGLISH_ALGERIA_KEYWORDS
from backend.collector.arabic_normalizer import normalize_arabic

logger = logging.getLogger(__name__)


# Keywords for "Algeria" in Arabic
ALGERIA_KEYWORDS_AR = [
    # core identifiers
    "الجزاير",
    "جزايري",
    "جزايريه",
    "الجزايري",
    "الجزايريه",
    "جزايريين",
    "جزايريون",
    "الجزايريين",
    "الجزايريون",


    # institutions
    "المجلس الشعبي الوطني",
    "مجلس الامه",
    "الجيش الوطني الشعبي",


    # energy / economy
    "سوناطراك",
    "نفطال",


    # sports
    "الخضر",
    "الفاف",

    # major cities
    "ادرار",
    "الشلف",
    "الاغواط",
    "ام البواقي",
    "باتنه",
    "بجايه",
    "بسكره",
    "بشار",
    "البليده",
    "البويره",
    "تمنراست",
    "تبسه",
    "تلمسان",
    "تيارت",
    "تيزي وزو",
    "الجزاير",
    "الجلفه",
    "جيجل",
    "سطيف",
    "سعيده",
    "سكيكده",
    "سيدي بلعباس",
    "عنابه",
    "قالمه",
    "قسنطينه",
    "المديه",
    "مستغانم",
    "المسيله",
    "معسكر",
    "ورقله",
    "وهران",
    "البيض",
    "اليزي",
    "برج بوعريريج",
    "بومرداس",
    "الطارف",
    "تندوف",
    "تيسمسيلت",
    "الوادي",
    "خنشله",
    "سوق اهراس",
    "تيبازة",
    "ميله",
    "عين الدفلي",
    "النعامه",
    "عين تموشنت",
    "غردايه",
    "غليزان",

    # wilayas created in 2019
    "تيميمون",
    "برج باجي مختار",
    "اولاد جلال",
    "بني عباس",
    "عين صالح",
    "عين قزام",
    "تقرت",
    "جانت",
    "المغير",
    "المنيعه",

    # wilayas created in 2025
    "افلو",
    "بريكه",
    "قصر الشلاله",
    "مسعد",
    "عين وساره",
    "بوسعاده",
    "الابيض سيدي الشيخ",
    "القنطره",
    "بير العاتر",
    "قصر البخاري",
    "العريشه"
]

_BOILERPLATE_RE = re.compile(
    r"(The post .*? appeared first on .*?\.)",
    re.IGNORECASE | re.DOTALL,
)

def _html_to_text(html: str) -> str:
    """Convert HTML snippet to plain text."""
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        return text
    except Exception:
        # If BeautifulSoup fails, return original string
        return html

def _remove_boilerplate(text: str) -> str:
    """Remove common RSS boilerplate like 'The post ... appeared first on ...'."""
    if not text:
        return ""
    return _BOILERPLATE_RE.sub("", text).strip()


def _safe_get(entry: Any, key: str, default: str = "") -> str:
    """Safely extract string fields from feedparser entries."""
    try:
        val = getattr(entry, key, None)
        if val is None and isinstance(entry, dict):
            val = entry.get(key, None)
        if val is None:
            return default
        return str(val).strip()
    except Exception:
        return default


def _extract_link(entry: Any) -> str:
    """
    Extract the best URL from an RSS entry.
    Try: link -> id -> links[0].href
    """
    link = _safe_get(entry, "link", "")
    if link:
        return link

    entry_id = _safe_get(entry, "id", "")
    if entry_id and entry_id.startswith("http"):
        return entry_id

    try:
        links = getattr(entry, "links", None) or (entry.get("links") if isinstance(entry, dict) else None)
        if links and isinstance(links, list):
            href = links[0].get("href") if isinstance(links[0], dict) else getattr(links[0], "href", "")
            if href:
                return str(href).strip()
    except Exception:
        pass

    return ""


def _extract_summary(entry: Any) -> str:
    """
    Extract a usable description/summary text.
    Try: summary -> description -> content[0].value
    """
    summary = _safe_get(entry, "summary", "")
    if summary:
        return summary

    desc = _safe_get(entry, "description", "")
    if desc:
        return desc

    try:
        content = getattr(entry, "content", None) or (entry.get("content") if isinstance(entry, dict) else None)
        if content and isinstance(content, list) and len(content) > 0:
            # feedparser often stores content as [{'type':..., 'value':...}]
            first = content[0]
            val = first.get("value") if isinstance(first, dict) else getattr(first, "value", "")
            if val:
                return str(val).strip()
    except Exception:
        pass

    return ""


def _extract_published(entry: Any) -> str:
    """
    Try multiple fields. We return a string as-is because DB layer might parse later.
    """
    published = _safe_get(entry, "published", "")
    if published:
        return published

    updated = _safe_get(entry, "updated", "")
    if updated:
        return updated

    # If parsed time exists, convert to ISO-ish string
    try:
        tp = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        if tp:
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", tp)
    except Exception:
        pass

    return ""


def is_algeria_related_ar(title_norm: str, body_norm: str) -> bool:
    """Keep an item if Algeria keywords appear in normalized title or normalized body."""
    haystack = f"{title_norm} {body_norm}".strip()
    if not haystack:
        return False
    return any(k in haystack for k in ALGERIA_KEYWORDS_AR)


def collect_arabic_rss(limit_per_source: int = 50) -> List[Dict[str, Any]]:
    """
    Collect Arabic RSS items for Algeria-related news only.

    Returns a list of dicts with both raw and normalized fields so downstream
    steps (scraper/dedup/db) can choose what they need.
    """
    articles: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()

    for src in ARABIC_RSS_SOURCES:
        source_name = src.get("name", "Unknown Source")
        rss_url = src.get("rss_url", "")
        language = src.get("language", "ar")
        region = src.get("region", "unknown")

        if not rss_url:
            continue

        feed = feedparser.parse(rss_url)
        entries = getattr(feed, "entries", []) or []
        if not entries:
            continue

        for entry in entries[:limit_per_source]:
            title_raw = _safe_get(entry, "title", "")
            summary_raw_html = _extract_summary(entry)
            summary_raw_text = _remove_boilerplate(_html_to_text(summary_raw_html))
            link = _extract_link(entry)
            published = _extract_published(entry)
            entry_id = _safe_get(entry, "id", "")

            # Skip junk entries
            if not title_raw and not link:
                continue

            # Local dedup by URL (RSS often repeats same entry)
            if link and link in seen_urls:
                continue
            if link:
                seen_urls.add(link)

            # Normalize once per field
            title_norm = normalize_arabic(title_raw, do_lang_detect=False).get("text", "")
            summary_norm_result = normalize_arabic(summary_raw_text)
            if summary_norm_result.get("language") != "ar":
                continue
            summary_norm = summary_norm_result.get("text", "")

            # Algeria keyword filter
            if not is_algeria_related_ar(title_norm, summary_norm):
                continue

            articles.append(
    {
        "source_name": source_name,
        "source_rss": rss_url,
        "language": language,
        "region": region,
        "entry_id": entry_id,
        "title_raw": title_raw,
        "title_norm": title_norm,
        "summary_raw": summary_raw_text,
        "summary_norm": summary_norm,
        "url": link,
        "published": published,
    }
)
            

    return articles


def is_algeria_related_en(title_en: str, body_en: str) -> bool:
    """Check if an English article is about Algeria by keyword matching."""
    haystack = f"{title_en} {body_en}".strip().lower()
    if not haystack:
        return False
    return any(k in haystack for k in ENGLISH_ALGERIA_KEYWORDS)


def collect_english_rss(limit_per_source: int = 50) -> List[Dict[str, Any]]:
    """
    Collect English RSS items for Algeria-related news.

    International sources (Al Jazeera, BBC, Reuters, etc.) are checked
    against Algeria keywords. Returns a list of dicts with article content.

    Args:
        limit_per_source: Max articles per RSS feed (default 50).

    Returns:
        List of article dicts in standardized format.
    """
    articles: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()

    for src in ENGLISH_RSS_SOURCES:
        source_name = src.get("name", "Unknown Source")
        rss_url = src.get("rss_url", "")
        language = src.get("language", "en")
        region = src.get("region", "international")

        if not rss_url:
            continue

        feed = feedparser.parse(rss_url)
        entries = getattr(feed, "entries", []) or []
        if not entries:
            continue

        for entry in entries[:limit_per_source]:
            title_raw = _safe_get(entry, "title", "")
            summary_raw_html = _extract_summary(entry)
            summary_raw_text = _remove_boilerplate(_html_to_text(summary_raw_html))
            link = _extract_link(entry)
            published = _extract_published(entry)

            # Skip junk entries
            if not title_raw and not link:
                continue

            # Local dedup by URL
            if link and link in seen_urls:
                continue
            if link:
                seen_urls.add(link)

            # Algeria keyword filter
            if not is_algeria_related_en(title_raw, summary_raw_text):
                continue

            articles.append({
                "source_name": source_name,
                "source_rss": rss_url,
                "language": language,
                "region": region,
                "title": title_raw.strip(),
                "summary": summary_raw_text.strip(),
                "url": link,
                "published": published,
            })

    return articles


def fetch_all_rss(limit_per_source: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch RSS articles from all available sources (Arabic + English).
    
    Aggregates content from:
    - Arabic RSS feeds (algerian local sources)
    - English RSS feeds (international sources filtered for Algeria content)
    
    Args:
        limit_per_source: Max articles per RSS feed.
    
    Returns:
        Aggregated list of article dicts from all RSS sources.
    """
    logger.info("Fetching articles from all RSS sources")
    all_articles: List[Dict[str, Any]] = []

    streams = [
        ("arabic_rss", collect_arabic_rss),
        ("english_rss", collect_english_rss),
    ]

    with ThreadPoolExecutor(max_workers=len(streams), thread_name_prefix="rss") as executor:
        futures = {
            executor.submit(fn, limit_per_source=limit_per_source): name
            for name, fn in streams
        }

        for future in as_completed(futures):
            stream_name = futures[future]
            try:
                items = future.result() or []
                all_articles.extend(items)
                logger.info("✓ %s: %d articles", stream_name, len(items))
            except Exception as exc:  # noqa: BLE001
                logger.exception("RSS stream %s failed: %s", stream_name, exc)

    logger.info("RSS collection complete: %d articles from all sources", len(all_articles))
    return all_articles


# if __name__ == "__main__":
#     results = collect_arabic_rss()

#     print(f"\nCollected Algeria-related Arabic RSS items: {len(results)}\n")

#     for r in results[:10]:
#         print("SOURCE:", r["source_name"])
#         print("TITLE:", r["title_raw"])
#         print("TITLE_norm:", r["title_norm"])
#         print("DESCRIPTION:", r["summary_raw"])
#         print("URL:", r["url"])
#         print("PUBLISHED:", r["published"])
#         print("-" * 60)