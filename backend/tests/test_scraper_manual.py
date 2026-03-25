import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from collector.scraper import scrape_article, _extract_domain, _detect_lang
from collector.apify_collector import needs_apify

print("=== Testing helpers ===")
print(f"domain: {_extract_domain('https://www.france24.com/fr/some-article')}")
print(f"detect lang (french text): {_detect_lang('Le président algérien a annoncé de nouvelles mesures économiques')}")
print(f"detect lang (short text): {_detect_lang('hello')}")
print()

print("=== Testing scrape_article with direct URLs ===")

test_urls = [
    ("https://www.lemonde.fr/afrique/article/2026/03/04/j-essaye-juste-d-oublier-le-passe-en-libye-les-jeunes-revent-d-un-avenir-meilleur-malgre-la-crise-economique_6669553_3212.html", "fr"),
    ("https://www.france24.com/fr/afrique/20240101-algérie-les-faits-marquants-de-2024", "fr"),
    ("https://www.aljazeera.net/news/2024/1/1/test", "ar"),
]

for url, lang in test_urls:
    print(f"\n--- {_extract_domain(url)} ---")
    print(f"  needs apify: {needs_apify(url)}")
    result = scrape_article(url, language=lang)
    if result:
        print(f"  title: {result['title']}")
        print(f"  language: {result['language']}")
        print(f"  text length: {len(result['full_text'])} chars")
        print(f"  preview: {result['full_text'][:150]}...")
    else:
        print(f"  extraction failed (needs APIFY_TOKEN for blocked sites)")
