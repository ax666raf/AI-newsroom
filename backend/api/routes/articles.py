from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.db import get_db
from backend.database.models import Article

router = APIRouter()

@router.get("/")
def get_articles(language: str = None, region: str = None, db: Session = Depends(get_db)):
    query = db.query(Article)
    if language:
        query = query.filter(Article.language == language)
    if region:
        query = query.filter(Article.region == region)
    return query.order_by(Article.collected_at.desc()).limit(100).all()