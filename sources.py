# =============================================================================
# sources.py — Amani's English News Sources Configuration
# =============================================================================

# ── RSS FEED SOURCES ──────────────────────────────────────────────────────────
# NOTE: Most Algerian outlets publish in Arabic/French — very few have English RSS.
# For English content, APIs (NewsAPI + Guardian) are the primary source.
# RSS here covers international outlets that report on Algeria in English.

RSS_SOURCES = [
    # ── International English outlets — keyword filter applied ──
    {
        "name": "Al Jazeera English",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "language": "en",
        "country": "international",
        "always_relevant": False,
    },
    {
        "name": "Middle East Eye",
        "url": "https://www.middleeasteye.net/rss",
        "language": "en",
        "country": "international",
        "always_relevant": False,
    },
    {
        "name": "The Africa Report",
        "url": "https://www.theafricareport.com/feed/",
        "language": "en",
        "country": "international",
        "always_relevant": False,
    },
    {
        "name": "BBC Africa",
        "url": "http://feeds.bbci.co.uk/news/world/africa/rss.xml",
        "language": "en",
        "country": "international",
        "always_relevant": False,
    },
    {
        "name": "France24 Africa EN",
        "url": "https://www.france24.com/en/africa/rss",
        "language": "en",
        "country": "international",
        "always_relevant": False,
    },
    {
        "name": "Reuters World News",
        "url": "https://feeds.reuters.com/Reuters/worldNews",
        "language": "en",
        "country": "international",
        "always_relevant": False,
    },
]

# ── NEWS API SOURCES ──────────────────────────────────────────────────────────
# 🔑 PASTE YOUR KEYS HERE (keep these secret — never push to GitHub)

NEWSAPI_CONFIG = {
    "base_url": "https://newsapi.org/v2/everything",
    "api_key":  "ecacec32f91e453da026645b9cfe02d2",   # newsapi.org
    "query":    "Algeria OR Algerian OR Algérie",
    "language": "en",
    "sort_by":  "publishedAt",
    "page_size": 100,
}

GUARDIAN_CONFIG = {
    "base_url": "https://content.guardianapis.com/search",
    "api_key":  "f0213ad6-38c9-4cf1-a869-8a796cf247c9",  # open-platform.theguardian.com
    "query":    "Algeria",
    "lang":     "en",
    "page_size": 50,
    "show_fields": "bodyText,headline,shortUrl",
}

# ── KEYWORD FILTER ────────────────────────────────────────────────────────────
ALGERIA_KEYWORDS = [
    "algeria", "algerian", "algérie", "algérienne",
    "alger", "algiers", "oran", "constantine",
    "tebboune", "sonatrach", "fln", "drs",
]