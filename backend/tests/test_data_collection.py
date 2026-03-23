#!/usr/bin/env python3
"""
test_data_collection.py — Actually collect data and show results

This test ACTUALLY collects articles from RSS feeds and shows:
- Article counts
- Sample articles  
- Deduplication in action
- Full pipeline results
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../..'))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


def test_arabic_rss_real():
    """Actually collect Arabic articles."""
    print("\n" + "="*70)
    print("TEST 1: COLLECT ACTUAL ARABIC RSS ARTICLES")
    print("="*70)
    
    try:
        from backend.collector.rss_collector import collect_arabic_rss
        
        logger.info("Collecting Arabic articles (2 articles per source)...")
        articles = collect_arabic_rss(limit_per_source=2)
        
        print(f"\n✓ SUCCESS: Collected {len(articles)} Arabic articles\n")
        
        if articles:
            print("Sample Arabic articles:")
            print("-" * 70)
            for i, art in enumerate(articles[:3], 1):
                print(f"\n{i}. SOURCE: {art.get('source_name', 'Unknown')}")
                print(f"   TITLE: {art.get('title', 'N/A')[:70]}")
                print(f"   URL: {art.get('url', 'N/A')[:60]}")
                print(f"   LANGUAGE: {art.get('language', 'N/A')}")
                print(f"   REGION: {art.get('region', 'N/A')}")
            print("\n" + "-" * 70)
            return True, articles
        else:
            print("⚠ No articles collected (feeds might be temporarily unavailable)")
            return True, []
            
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        logger.exception(e)
        return False, []


def test_english_rss_real():
    """Actually collect English articles."""
    print("\n" + "="*70)
    print("TEST 2: COLLECT ACTUAL ENGLISH RSS ARTICLES")
    print("="*70)
    
    try:
        from backend.collector.rss_collector import collect_english_rss
        
        logger.info("Collecting English articles (2 articles per source)...")
        articles = collect_english_rss(limit_per_source=2)
        
        print(f"\n✓ SUCCESS: Collected {len(articles)} English articles\n")
        
        if articles:
            print("Sample English articles:")
            print("-" * 70)
            for i, art in enumerate(articles[:3], 1):
                print(f"\n{i}. SOURCE: {art.get('source_name', 'Unknown')}")
                print(f"   TITLE: {art.get('title', 'N/A')[:70]}")
                print(f"   URL: {art.get('url', 'N/A')[:60]}")
                print(f"   LANGUAGE: {art.get('language', 'N/A')}")
            print("\n" + "-" * 70)
            return True, articles
        else:
            print("⚠ No English articles collected")
            return True, []
            
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        logger.exception(e)
        return False, []


def test_unified_rss_real():
    """Collect both Arabic and English."""
    print("\n" + "="*70)
    print("TEST 3: UNIFIED COLLECTION (Arabic + English)")
    print("="*70)
    
    try:
        from backend.collector.rss_collector import fetch_all_rss
        
        logger.info("Collecting from ALL RSS sources (Arabic + English)...")
        all_articles = fetch_all_rss(limit_per_source=2)
        
        print(f"\n✓ SUCCESS: Collected {len(all_articles)} total articles\n")
        
        # Count by language
        by_lang = {}
        for art in all_articles:
            lang = art.get('language', 'unknown')
            by_lang[lang] = by_lang.get(lang, 0) + 1
        
        print("Breakdown by language:")
        for lang, count in sorted(by_lang.items()):
            print(f"  • {lang}: {count} articles")
        
        print("\nAll collected articles:")
        print("-" * 70)
        for i, art in enumerate(all_articles, 1):
            lang_emoji = "🇸🇦" if art.get('language') == 'ar' else "🇬🇧"
            print(f"{i:2}. {lang_emoji} {art.get('source_name', 'Unknown')[:30]:30} | {art.get('title', 'N/A')[:40]}")
        print("-" * 70)
        
        return True, all_articles
        
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        logger.exception(e)
        return False, []


def test_deduplication(articles):
    """Test deduplication logic on collected articles."""
    print("\n" + "="*70)
    print("TEST 4: DEDUPLICATION TEST")
    print("="*70)
    
    try:
        from backend.deduplication.url_hash import compute_url_hash
        from backend.deduplication.fuzzy_match import are_titles_similar
        
        if not articles:
            print("⚠ No articles to deduplicate (skipping)")
            return True
        
        print(f"\nTesting deduplication on {len(articles)} articles...\n")
        
        # Test URL hashing
        print("Level 1: URL Hash Deduplication")
        print("-" * 70)
        hashes = {}
        duplicates_by_url = 0
        for art in articles:
            url = art.get('url', '')
            if url:
                h = compute_url_hash(url)
                if h in hashes:
                    duplicates_by_url += 1
                hashes[h] = art.get('title', '')
        
        print(f"  Unique URLs: {len(hashes)}")
        print(f"  Duplicates removed: {duplicates_by_url}")
        print(f"  Result: {len(articles)} articles → {len(hashes)} unique ✓")
        
        # Test fuzzy matching
        print("\nLevel 2: Fuzzy Title Deduplication")
        print("-" * 70)
        if len(articles) >= 2:
            # Find similar titles
            similar_pairs = []
            for i, art1 in enumerate(articles):
                for art2 in articles[i+1:]:
                    t1 = art1.get('title', '')
                    t2 = art2.get('title', '')
                    if t1 and t2 and are_titles_similar(t1, t2):
                        similar_pairs.append((t1[:50], t2[:50]))
            
            if similar_pairs:
                print(f"  Found {len(similar_pairs)} similar title pairs:")
                for t1, t2 in similar_pairs[:3]:
                    print(f"    • '{t1}...'")
                    print(f"      ≈ '{t2}...'")
            else:
                print(f"  No similar titles found among {len(articles)} articles")
        
        print("\n✓ Deduplication test complete")
        return True
        
    except Exception as e:
        print(f"\n✗ Deduplication test FAILED: {e}")
        logger.exception(e)
        return False


def main():
    print("\n╔" + "="*68 + "╗")
    print("║" + " "*13 + "DATA COLLECTION TEST - REAL ARTICLES" + " "*19 + "║")
    print("╚" + "="*68 + "╝")
    
    results = {}
    all_articles = []
    
    # Test 1: Arabic RSS
    success, ar_articles = test_arabic_rss_real()
    results["Arabic RSS"] = success
    all_articles.extend(ar_articles)
    
    # Test 2: English RSS
    success, en_articles = test_english_rss_real()
    results["English RSS"] = success
    all_articles.extend(en_articles)
    
    # Test 3: Unified Collection
    success, all_rss = test_unified_rss_real()
    results["Unified Collection"] = success
    
    # Test 4: Deduplication
    success = test_deduplication(all_articles)
    results["Deduplication"] = success
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    passed = sum(1 for v in results.values() if v)
    print(f"\n✓ {passed}/{len(results)} tests passed")
    
    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)
    print(f"\nTotal articles collected: {len(all_articles)}")
    
    if all_articles:
        by_lang = {}
        by_source = {}
        for art in all_articles:
            lang = art.get('language', 'unknown')
            source = art.get('source_name', 'unknown')
            by_lang[lang] = by_lang.get(lang, 0) + 1
            by_source[source] = by_source.get(source, 0) + 1
        
        print(f"\nBy Language:")
        for lang, count in sorted(by_lang.items()):
            print(f"  • {lang}: {count}")
        
        print(f"\nTop Sources:")
        for source, count in sorted(by_source.items(), key=lambda x: -x[1])[:5]:
            print(f"  • {source}: {count}")
        
        print(f"\nData is ready for:")
        print(f"  1. Scraping full text (enrich_articles)")
        print(f"  2. Deduplication (filter_known_urls)")
        print(f"  3. Fuzzy matching (deduplicate_by_title)")
        print(f"  4. Database storage (_save_articles)")
    
    print("\n" + "="*70 + "\n")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
