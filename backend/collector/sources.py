"""
sources.py — Master list of Algerian news sources.

Every source has:
  name      : human-readable label
  url       : homepage (for display / scraping fallback)
  rss       : RSS/Atom feed URL  (None if not available)
  language  : "ar" | "fr" | "en"
  tier      : "primary" | "secondary"  (affects dedup priority)
  category  : default category tag
"""

SOURCES = [
    # ------------------------------------------------------------------ ARABIC
    {
        "name": "الشروق أونلاين",
        "url": "https://www.echoroukonline.com",
        "rss": "https://www.echoroukonline.com/feed",
        "language": "ar",
        "tier": "primary",
        "category": "general",
    },
    {
        "name": "النهار أونلاين",
        "url": "https://www.ennaharonline.com",
        "rss": "https://www.ennaharonline.com/feed",
        "language": "ar",
        "tier": "primary",
        "category": "general",
    },
    {
        "name": "الخبر",
        "url": "https://www.elkhabar.com",
        "rss": "https://www.elkhabar.com/feed",
        "language": "ar",
        "tier": "primary",
        "category": "general",
    },
    {
        "name": "البلاد",
        "url": "https://www.elbilad.net",
        "rss": "https://www.elbilad.net/feed",
        "language": "ar",
        "tier": "secondary",
        "category": "general",
    },
    {
        "name": "الوطن",
        "url": "https://www.elwatan.com.dz",
        "rss": "https://www.elwatan.com.dz/feed",
        "language": "ar",
        "tier": "secondary",
        "category": "general",
    },
    {
        "name": "وكالة الأنباء الجزائرية",
        "url": "https://www.aps.dz/ar",
        "rss": "https://www.aps.dz/ar/?format=feed&type=rss",
        "language": "ar",
        "tier": "primary",
        "category": "official",
    },
    # ------------------------------------------------------------------ FRENCH
    {
        "name": "TSA Algérie",
        "url": "https://www.tsa-algerie.com",
        "rss": "https://www.tsa-algerie.com/feed",
        "language": "fr",
        "tier": "primary",
        "category": "general",
    },
    {
        "name": "El Watan",
        "url": "https://www.elwatan.com",
        "rss": "https://www.elwatan.com/feed",
        "language": "fr",
        "tier": "primary",
        "category": "general",
    },
    {
        "name": "Liberté Algérie",
        "url": "https://www.liberte-algerie.com",
        "rss": "https://www.liberte-algerie.com/feed",
        "language": "fr",
        "tier": "primary",
        "category": "general",
    },
    {
        "name": "Le Soir d'Algérie",
        "url": "https://www.lesoirdalgerie.com",
        "rss": "https://www.lesoirdalgerie.com/feed",
        "language": "fr",
        "tier": "secondary",
        "category": "general",
    },
    {
        "name": "El Moudjahid",
        "url": "https://www.elmoudjahid.com",
        "rss": "https://www.elmoudjahid.com/feed",
        "language": "fr",
        "tier": "secondary",
        "category": "official",
    },
    {
        "name": "Algérie Presse Service (FR)",
        "url": "https://www.aps.dz/fr",
        "rss": "https://www.aps.dz/fr/?format=feed&type=rss",
        "language": "fr",
        "tier": "primary",
        "category": "official",
    },
    # ------------------------------------------------------------------ ENGLISH
    {
        "name": "Algeria Press Service (EN)",
        "url": "https://www.aps.dz/en",
        "rss": "https://www.aps.dz/en/?format=feed&type=rss",
        "language": "en",
        "tier": "primary",
        "category": "official",
    },
    {
        "name": "The North Africa Post",
        "url": "https://northafricapost.com",
        "rss": "https://northafricapost.com/feed",
        "language": "en",
        "tier": "secondary",
        "category": "general",
    },
    {
        "name": "Middle East Eye — Algeria",
        "url": "https://www.middleeasteye.net/countries/algeria",
        "rss": "https://www.middleeasteye.net/rss/algeria",
        "language": "en",
        "tier": "secondary",
        "category": "general",
    },
    {
        "name": "Maghreb Emergent",
        "url": "https://maghrebemergent.info",
        "rss": "https://maghrebemergent.info/feed",
        "language": "fr",
        "tier": "secondary",
        "category": "economy",
    },
]

# Convenient filtered views
def get_sources_by_language(lang: str) -> list:
    """Return sources filtered by language code: 'ar', 'fr', or 'en'."""
    return [s for s in SOURCES if s["language"] == lang]

def get_rss_sources() -> list:
    """Return only sources that have a valid RSS feed."""
    return [s for s in SOURCES if s.get("rss")]

def get_primary_sources() -> list:
    return [s for s in SOURCES if s["tier"] == "primary"]
