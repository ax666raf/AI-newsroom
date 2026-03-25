"""
models.py — Full database schema for the AI Newsroom.

Tables:
  articles        — Every collected article (deduplicated)
  story_groups    — Clusters of articles about the same story
  collection_logs — Audit trail for pipeline runs

Key design decisions:
    • url_hash (MD5)       → Level 1 dedup: instant, exact-URL duplicate rejection
  • embedding (vector)   → Level 3 dedup + RAG retrieval via pgvector
  • group_id FK          → Links an article to its StoryGroup cluster
  • Indexes on url_hash, language, group_id for fast lookups
"""

from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


# ──────────────────────────────────────────────────── Base
class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────────── Articles
class Article(Base):
    __tablename__ = "articles"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    title        = Column(String(500), nullable=False)
    url          = Column(String(1000), nullable=False, unique=True)
    url_hash     = Column(String(32), nullable=False, unique=True, index=True)
    full_text    = Column(Text, nullable=True)
    summary      = Column(Text, nullable=True)            # AI-generated summary (filled later)
    source_name  = Column(String(200), nullable=False)
    language     = Column(String(10), nullable=False)      # "ar" | "fr" | "en"
    region       = Column(String(50), default="algeria")
    category     = Column(String(100), default="general")
    published_at = Column(DateTime(timezone=True), nullable=True)
    collected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Vector embedding for semantic search / RAG  (384-dim for MiniLM)
    embedding = Column(Vector(384), nullable=True)

    # ── Dedup / grouping
    is_duplicate = Column(Boolean, default=False, nullable=False)
    group_id     = Column(
        Integer,
        ForeignKey("story_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationship
    group = relationship("StoryGroup", back_populates="articles")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_articles_lang_collected", "language", "collected_at"),
        Index("ix_articles_published", "published_at"),
    )

    def __repr__(self):
        return f"<Article id={self.id} src={self.source_name!r} lang={self.language}>"


# ──────────────────────────────────────────────────── Story Groups
class StoryGroup(Base):
    """
    A cluster of articles that all report the same underlying story.

    Created by the dedup/grouping pipeline.  AI processing later fills:
      neutral_title, summary, why_it_matters
    """
    __tablename__ = "story_groups"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    primary_title  = Column(String(500), nullable=False)
    neutral_title  = Column(String(500), nullable=True)     # AI-rewritten headline
    summary        = Column(Text, nullable=True)            # AI-generated summary
    why_it_matters = Column(Text, nullable=True)            # AI explanation
    category       = Column(String(100), default="general")
    coverage_count = Column(Integer, default=1, nullable=False)
    source_names   = Column(ARRAY(String), default=[])      # list of source names
    languages      = Column(ARRAY(String), default=[])      # languages covering this story
    region         = Column(String(50), default="algeria")

    # Representative embedding (centroid of member articles)
    representative_embedding = Column(Vector(384), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship
    articles = relationship("Article", back_populates="group", lazy="dynamic")

    def __repr__(self):
        return f"<StoryGroup id={self.id} count={self.coverage_count} title={self.primary_title[:40]!r}>"


# ──────────────────────────────────────────────────── Collection Logs
class CollectionLog(Base):
    """Audit log written after every pipeline run."""
    __tablename__ = "collection_logs"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    run_at         = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    articles_found = Column(Integer, default=0)
    duplicates     = Column(Integer, default=0)
    new_stories    = Column(Integer, default=0)
    groups_created = Column(Integer, default=0)
    status         = Column(String(50), nullable=False)    # "success" | "partial" | "failed"
    notes          = Column(Text, nullable=True)

    def __repr__(self):
        return f"<CollectionLog id={self.id} status={self.status!r} new={self.new_stories}>"
