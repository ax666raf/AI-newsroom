from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database.db import get_db
from backend.database.models import Article

router = APIRouter()


def _article_to_dict(article: Article) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "url": article.url,
        "url_hash": article.url_hash,
        "full_text": article.full_text,
        "summary": article.summary,
        "source_name": article.source_name,
        "language": article.language,
        "region": article.region,
        "category": article.category,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "collected_at": article.collected_at.isoformat() if article.collected_at else None,
        "is_duplicate": bool(article.is_duplicate),
        "group_id": article.group_id,
    }


@router.get("")
@router.get("/")
def get_articles(
    language: str | None = Query(default=None),
    region: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(Article)
    if language:
        query = query.filter(Article.language == language)
    if region:
        query = query.filter(Article.region == region)

    rows = query.order_by(Article.collected_at.desc()).limit(limit).all()
    return {
        "count": len(rows),
        "items": [_article_to_dict(article) for article in rows],
    }