"""
fuzzy_match.py — Level 2 Deduplication: near-duplicate titles via rapidfuzz.

After Level 1 (URL-hash) removes exact-URL copies, two different URLs
can still report the same story with slightly different titles:

  رئيس الجمهورية يستقبل وزير الخارجية الإيطالي
  الرئيس تبون يلتقي بوزير خارجية إيطاليا

Level 2 catches these by comparing titles with token-sort ratio
(order-insensitive fuzzy matching).  Works for Arabic, French, English.

Complexity: O(n²) but n is small after Level 1 filtering (~tens of articles).
"""

import logging
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Threshold: 0-100. 75 balances recall/precision for multilingual headlines.
SIMILARITY_THRESHOLD = 75


def _normalise_title(title: str) -> str:
    """
    Light normalisation before fuzzy comparison.
    Heavy Arabic normalisation is handled by the arabic_normalizer
    module (teammate's responsibility) — we just do basics here.
    """
    return title.strip().lower()


def are_titles_similar(title_a: str, title_b: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    """
    Return True if two titles are near-duplicates.

    Uses token_sort_ratio which:
      • Tokenises both strings
      • Sorts tokens alphabetically
      • Computes Levenshtein-based similarity
    This makes it robust to word-order differences — very common
    in Arabic (VSO/SVO flexibility) and French headline styles.
    """
    a = _normalise_title(title_a)
    b = _normalise_title(title_b)
    score = fuzz.token_sort_ratio(a, b)
    return score >= threshold


def deduplicate_by_title(
    articles: list[dict],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict]:
    """
    Remove near-duplicate articles based on title similarity.

    Algorithm:
      1. Walk through articles in order (earlier = higher priority).
      2. For each article, compare its title against all already-accepted titles.
      3. If it matches any accepted title above `threshold` → mark as duplicate.
      4. Otherwise → accept it.

    Returns:
        New list with duplicates removed.
    """
    if not articles:
        return []

    accepted: list[dict] = []
    duplicates_found = 0

    for article in articles:
        title = article.get("title", "")
        if not title:
            accepted.append(article)
            continue

        is_dup = False
        for kept in accepted:
            if are_titles_similar(title, kept.get("title", ""), threshold):
                is_dup = True
                # Keep the article from the "primary" tier source if available
                logger.debug(
                    "Fuzzy dup: %r \u2248 %r (score ≥ %d)",
                    title[:60], kept["title"][:60], threshold,
                )
                break

        if is_dup:
            duplicates_found += 1
        else:
            accepted.append(article)

    logger.info(
        "Fuzzy-title dedup: %d incoming → %d unique, %d near-duplicates removed",
        len(articles), len(accepted), duplicates_found,
    )
    return accepted


def find_similar_titles(
    new_title: str,
    existing_titles: list[str],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[tuple[int, float]]:
    """
    Utility: given a new title, return indices + scores of similar existing titles.
    Useful for the grouping step.
    """
    results = []
    norm_new = _normalise_title(new_title)
    for idx, existing in enumerate(existing_titles):
        score = fuzz.token_sort_ratio(norm_new, _normalise_title(existing))
        if score >= threshold:
            results.append((idx, score))
    return sorted(results, key=lambda x: x[1], reverse=True)
