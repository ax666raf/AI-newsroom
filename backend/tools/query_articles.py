#!/usr/bin/env python3
"""
query_articles.py — Simple tool to query articles from PostgreSQL.

Usage:
    python3 tools/query_articles.py --all              # Show all articles
    python3 tools/query_articles.py --latest 10        # Show latest 10
    python3 tools/query_articles.py --lang ar          # Show Arabic articles
    python3 tools/query_articles.py --source "النهار"  # Show from source
    python3 tools/query_articles.py --search "keyword" # Search titles
"""

import argparse
from backend.database.db import SessionLocal
from backend.database.models import Article
from sqlalchemy import func, or_
from datetime import datetime

session = SessionLocal()


def show_all():
    """Display all articles."""
    articles = session.query(Article).order_by(Article.published_at.desc()).all()
    print(f"\n📰 Total articles: {len(articles)}\n")
    for i, a in enumerate(articles, 1):
        print(f"{i}. {a.source_name} ({a.language})")
        print(f"   {a.title[:70]}")
        print(f"   {a.url}\n")


def show_latest(n=10):
    """Show latest N articles."""
    articles = session.query(Article).order_by(Article.published_at.desc()).limit(n).all()
    print(f"\n📝 Latest {n} articles:\n")
    for i, a in enumerate(articles, 1):
        print(f"{i}. [{a.language.upper()}] {a.source_name}")
        print(f"   {a.title[:70]}")
        if a.published_at:
            print(f"   Published: {a.published_at.strftime('%Y-%m-%d %H:%M')}")
        print()


def show_by_language(lang):
    """Show articles in specific language."""
    articles = session.query(Article).filter(Article.language == lang).all()
    lang_name = {'ar': 'Arabic 🇸🇦', 'fr': 'French 🇫🇷', 'en': 'English 🇬🇧'}.get(lang, lang)
    print(f"\n{lang_name}: {len(articles)} articles\n")
    for a in articles[:10]:
        print(f"• {a.source_name}: {a.title[:60]}")


def show_by_source(source):
    """Show articles from specific source."""
    articles = session.query(Article).filter(
        Article.source_name.ilike(f"%{source}%")
    ).all()
    print(f"\nFrom '{source}': {len(articles)} articles\n")
    for a in articles:
        print(f"• {a.title[:70]}")


def search(keyword):
    """Search articles by title or URL."""
    articles = session.query(Article).filter(
        or_(
            Article.title.ilike(f"%{keyword}%"),
            Article.url.ilike(f"%{keyword}%"),
        )
    ).all()
    print(f"\nSearch '{keyword}': {len(articles)} results\n")
    for a in articles:
        print(f"• {a.source_name}: {a.title[:70]}")


def stats():
    """Show database statistics."""
    total = session.query(Article).count()
    
    print("\n" + "=" * 70)
    print("DATABASE STATISTICS")
    print("=" * 70)
    
    print(f"\nTotal articles: {total}\n")
    
    print("By Language:")
    langs = session.query(Article.language, func.count()).group_by(Article.language).all()
    lang_map = {'ar': '🇸🇦 Arabic', 'fr': '🇫🇷 French', 'en': '🇬🇧 English'}
    for lang, count in langs:
        print(f"  • {lang_map.get(lang, lang)}: {count}")
    
    print("\nTop 5 Sources:")
    sources = session.query(Article.source_name, func.count()).group_by(
        Article.source_name
    ).order_by(func.count().desc()).limit(5).all()
    for source, count in sources:
        print(f"  • {source}: {count}")
    
    if total > 0:
        earliest = session.query(Article).order_by(Article.published_at).first()
        latest = session.query(Article).order_by(Article.published_at.desc()).first()
        print(f"\nDate Range:")
        print(f"  • Oldest: {earliest.published_at or 'N/A'}")
        print(f"  • Latest: {latest.published_at or 'N/A'}")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query articles from database")
    parser.add_argument("--all", action="store_true", help="Show all articles")
    parser.add_argument("--latest", type=int, metavar="N", help="Show latest N articles")
    parser.add_argument("--lang", metavar="LANG", help="Filter by language (ar/fr/en)")
    parser.add_argument("--source", metavar="SOURCE", help="Filter by source name")
    parser.add_argument("--search", metavar="KEYWORD", help="Search by keyword")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    
    args = parser.parse_args()
    
    if args.all:
        show_all()
    elif args.latest:
        show_latest(args.latest)
    elif args.lang:
        show_by_language(args.lang)
    elif args.source:
        show_by_source(args.source)
    elif args.search:
        search(args.search)
    elif args.stats:
        stats()
    else:
        # Default: show stats
        stats()
    
    session.close()
