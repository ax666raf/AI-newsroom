# Database models
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Article(Base):
    __tablename__ = "articles"

    id           = Column(Integer, primary_key=True)
    title        = Column(String(500))
    url          = Column(String(1000), unique=True)
    url_hash     = Column(String(64), unique=True)
    full_text    = Column(Text)
    summary      = Column(Text)
    source_name  = Column(String(200))
    language     = Column(String(10))       # "ar", "fr", "en"
    region       = Column(String(50))       # "global", "arab_world", "algeria"
    category     = Column(String(100))
    published_at = Column(DateTime)
    collected_at = Column(DateTime, default=datetime.utcnow)
    embedding    = Column(ARRAY(Float))     # semantic vector stored in DB
    group_id     = Column(Integer, nullable=True)

class StoryGroup(Base):
    __tablename__ = "story_groups"

    id             = Column(Integer, primary_key=True)
    primary_title  = Column(String(500))
    neutral_title  = Column(String(500))    # AI-rewritten headline
    summary        = Column(Text)           # AI-generated summary
    why_it_matters = Column(Text)           # AI explanation
    coverage_count = Column(Integer, default=1)
    sources        = Column(ARRAY(String))
    languages      = Column(ARRAY(String))
    region         = Column(String(50))
    created_at     = Column(DateTime, default=datetime.utcnow)

class CollectionLog(Base):
    __tablename__ = "collection_logs"

    id             = Column(Integer, primary_key=True)
    run_at         = Column(DateTime, default=datetime.utcnow)
    articles_found = Column(Integer)
    duplicates     = Column(Integer)
    new_stories    = Column(Integer)
    status         = Column(String(50))     # "success" / "partial" / "failed"
    notes          = Column(Text)