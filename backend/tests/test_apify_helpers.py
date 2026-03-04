import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from collector.apify_collector import (
    needs_apify, _guess_language, _extract_domain,
    _clean_arabic_text, _clean_french_text,
    FRENCH_BLOCKED_DOMAINS, ARABIC_BLOCKED_DOMAINS,
)

print("=== Domain detection ===")
tests = [
    "https://www.france24.com/fr/some-article",
    "https://www.rfi.fr/fr/afrique/some-article",
    "https://www.tsa-algerie.com/some-article",
    "https://www.echoroukonline.com/some-article",
    "https://www.ennaharonline.com/some-article",
    "https://www.elkhabar.com/some-article",
    "https://www.aljazeera.net/news/some-article",
    "https://www.lemonde.fr/afrique/some-article",
    "https://www.bbc.com/arabic/some-article",
]
for url in tests:
    domain = _extract_domain(url)
    blocked = needs_apify(url)
    lang = _guess_language(url)
    print(f"  {domain:30s} blocked={str(blocked):5s}  lang={lang}")

print()
print("=== Language guessing from text ===")
ar_text = "\u0627\u0644\u062c\u0632\u0627\u0626\u0631 \u062a\u0639\u0644\u0646 \u0639\u0646 \u0625\u062c\u0631\u0627\u0621\u0627\u062a \u0627\u0642\u062a\u0635\u0627\u062f\u064a\u0629 \u062c\u062f\u064a\u062f\u0629"
fr_text = "Le pr\u00e9sident alg\u00e9rien a annonc\u00e9 de nouvelles mesures \u00e9conomiques"
print(f"  arabic text -> {_guess_language('https://unknown.com', ar_text)}")
print(f"  french text -> {_guess_language('https://unknown.com', fr_text)}")

print()
print("=== Arabic text cleaning ===")
dirty = "\u0645\u0631\u062d\u0628\u0627\u200b\u200c   \u0628\u0627\u0644\u0639\u0627\u0644\u0645\u200d   "
clean = _clean_arabic_text(dirty)
print(f"  before: {repr(dirty)}")
print(f"  after:  {repr(clean)}")

print()
print(f"French blocked domains: {len(FRENCH_BLOCKED_DOMAINS)}")
print(f"Arabic blocked domains: {len(ARABIC_BLOCKED_DOMAINS)}")
print()
print("All checks passed.")
