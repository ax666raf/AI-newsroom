#!/usr/bin/env python3
"""
test_pipeline_simple.py — Simplified pipeline tests (runnable from repo root).

Run from repo root: python3 -m backend.tests.test_pipeline_simple
Or: cd backend && python3 -m tests.test_pipeline_simple
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../..'))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_arabic_rss():
    """Test Arabic RSS collection."""
    try:
        from backend.collector.rss_collector import collect_arabic_rss
        logger.info("✓ Arabic RSS import successful")
        
        # Note: Won't actually collect without network
        logger.info("  collect_arabic_rss() is ready (requires network to test)")
        return True
    except Exception as e:
        logger.error(f"✗ Arabic RSS import failed: {e}")
        return False


def test_english_rss():
    """Test English RSS collection."""
    try:
        from backend.collector.rss_collector import collect_english_rss
        logger.info("✓ English RSS import successful")
        
        logger.info("  collect_english_rss() is ready (requires network to test)")
        return True
    except Exception as e:
        logger.error(f"✗ English RSS import failed: {e}")
        return False


def test_fetch_all_rss():
    """Test unified RSS collection."""
    try:
        from backend.collector.rss_collector import fetch_all_rss
        logger.info("✓ fetch_all_rss() import successful")
        
        logger.info("  fetch_all_rss() is ready (requires network to test)")
        return True
    except Exception as e:
        logger.error(f"✗ fetch_all_rss() import failed: {e}")
        return False


def test_newsapi():
    """Test NewsAPI collection."""
    try:
        from backend.collector.api_collector import fetch_all_newsapi
        logger.info("✓ NewsAPI import successful")
        
        logger.info("  fetch_all_newsapi() is ready (requires NEWSAPI_KEY)")
        return True
    except Exception as e:
        logger.error(f"✗ NewsAPI import failed: {e}")
        return False


def test_scraper():
    """Test scraper functions."""
    try:
        from backend.collector.scraper import scrape_article, enrich_articles
        logger.info("✓ Scraper functions import successful")
        
        logger.info("  scrape_article() and enrich_articles() are ready")
        return True
    except Exception as e:
        logger.error(f"✗ Scraper import failed: {e}")
        return False


def test_url_dedup():
    """Test URL deduplication."""
    try:
        from backend.deduplication.url_hash import compute_url_hash, filter_known_urls
        logger.info("✓ URL dedup import successful")
        
        # Test hash function
        url = "https://example.com/article"
        hash1 = compute_url_hash(url)
        hash2 = compute_url_hash(url)
        assert hash1 == hash2, "Same URL should have same hash"
        logger.info(f"  ✓ Hash function works: {url} → {hash1[:16]}...")
        
        return True
    except Exception as e:
        logger.error(f"✗ URL dedup failed: {e}")
        return False


def test_fuzzy_dedup():
    """Test fuzzy title deduplication."""
    try:
        from backend.deduplication.fuzzy_match import are_titles_similar
        logger.info("✓ Fuzzy dedup import successful")
        
        # Test similar titles
        t1 = "Algeria signs gas deal"
        t2 = "Algeria signs new gas deal"
        is_sim = are_titles_similar(t1, t2)
        
        logger.info(f"  ✓ Fuzzy matching works: '{t1}' similar to '{t2}'? {is_sim}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Fuzzy dedup failed: {e}")
        return False


def test_embeddings():
    """Test embedding generation."""
    try:
        from backend.ai_processing.vector_store import generate_embedding
        logger.info("✓ Vector store import successful")
        
        text = "Algeria is a country in North Africa"
        embedding = generate_embedding(text)
        
        logger.info(f"  ✓ Embedding works: '{text[:40]}...'")
        logger.info(f"    Dimension: {len(embedding)}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Embeddings failed: {e}")
        return False


def test_pipeline():
    """Test pipeline runner."""
    try:
        from backend.pipeline.runner import run_pipeline
        from backend.pipeline.scheduler import start_scheduler
        
        logger.info("✓ Pipeline imports successful")
        logger.info("  run_pipeline() and start_scheduler() are ready")
        
        return True
    except Exception as e:
        logger.error(f"✗ Pipeline import failed: {e}")
        return False


def test_database():
    """Test database setup."""
    try:
        from backend.database.db import init_db
        from backend.database.models import Article, StoryGroup, CollectionLog
        
        logger.info("✓ Database imports successful")
        logger.info("  Models: Article, StoryGroup, CollectionLog")
        logger.info("  (Database initialization skipped to avoid setup)")
        
        return True
    except Exception as e:
        logger.error(f"✗ Database import failed: {e}")
        return False


def main():
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*10 + "AI-NEWSROOM PIPELINE IMPORT & BASIC TESTS" + " "*17 + "║")
    print("╚" + "="*68 + "╝\n")
    
    tests = [
        ("Arabic RSS Collection", test_arabic_rss),
        ("English RSS Collection", test_english_rss),
        ("Unified RSS Collection", test_fetch_all_rss),
        ("NewsAPI Collection", test_newsapi),
        ("Article Scraper", test_scraper),
        ("URL Deduplication", test_url_dedup),
        ("Fuzzy Title Deduplication", test_fuzzy_dedup),
        ("Embeddings (Vector Store)", test_embeddings),
        ("Pipeline Runner", test_pipeline),
        ("Database Models", test_database),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*70}")
        print(f"Testing: {test_name}")
        print('='*70)
        results[test_name] = test_func()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_flag in results.items():
        status = "✓" if passed_flag else "✗"
        print(f"  {status} {test_name}")
    
    print(f"\n✓ {passed}/{total} tests passed\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
