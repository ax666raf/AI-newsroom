"""
vector_store.py — Embedding generation + pgvector similarity search.

Responsibilities:
  1. Generate 384-dim embeddings using sentence-transformers (MiniLM)
  2. Store embeddings in the Article.embedding column (pgvector)
  3. Provide cosine-similarity search for:
       • Level 3 semantic deduplication
       • RAG retrieval (find relevant articles for a query)

The model 'paraphrase-multilingual-MiniLM-L12-v2' was chosen because:
  • Supports Arabic, French, English natively
  • 384 dimensions — fast and storage-efficient
  • Good quality for news headline / paragraph similarity
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sentence_transformers import SentenceTransformer
from sqlalchemy import select

from backend.database.db import get_db_session
from backend.database.models import Article

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────── Model Loading
# Lazy-loaded singleton so we don't load the model until first use
_model: Optional[SentenceTransformer] = None

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384


def _get_model() -> SentenceTransformer:
    """Load the sentence-transformer model (once)."""
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s ...", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded (%d-dim embeddings)", EMBEDDING_DIM)
    return _model


# ──────────────────────────────────────────────── Embedding Generation

def generate_embedding(text: str) -> list[float]:
    """
    Generate a single 384-dim embedding vector for a piece of text.

    Args:
        text: The article title, summary, or concatenated content.

    Returns:
        List of 384 floats (normalised unit vector).
    """
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def generate_embeddings_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts efficiently.

    Args:
        texts:      List of strings to embed.
        batch_size: Internal batch size for the model.

    Returns:
        List of embedding vectors (same order as input).
    """
    model = _get_model()
    vectors = model.encode(texts, batch_size=batch_size, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


# ──────────────────────────────────────────────── Store Embeddings in DB

def embed_article(article_id: int) -> bool:
    """
    Generate and store an embedding for a single article.

    Uses title + first 500 chars of summary/full_text as input.
    Returns True if successful.
    """
    with get_db_session() as session:
        article = session.get(Article, article_id)
        if article is None:
            logger.warning("Article %d not found", article_id)
            return False

        if article.embedding is not None:
            logger.debug("Article %d already has an embedding", article_id)
            return True

        # Build the text to embed: title + context
        parts = [article.title or ""]
        if article.summary:
            parts.append(article.summary[:500])
        elif article.full_text:
            parts.append(article.full_text[:500])

        combined = " — ".join(p for p in parts if p)
        if not combined.strip():
            logger.warning("Article %d has no text to embed", article_id)
            return False

        embedding = generate_embedding(combined)
        article.embedding = embedding
        session.commit()
        return True


def embed_unprocessed_articles(limit: int = 200) -> int:
    """
    Find articles without embeddings and generate them in batch.

    Args:
        limit: Max articles to process in one call.

    Returns:
        Number of articles embedded.
    """
    with get_db_session() as session:
        stmt = (
            select(Article)
            .where(Article.embedding.is_(None))
            .order_by(Article.collected_at.desc())
            .limit(limit)
        )
        articles = list(session.scalars(stmt))

        if not articles:
            logger.info("No unprocessed articles to embed")
            return 0

        # Build combined texts
        texts = []
        for a in articles:
            parts = [a.title or ""]
            if a.summary:
                parts.append(a.summary[:500])
            elif a.full_text:
                parts.append(a.full_text[:500])
            texts.append(" — ".join(p for p in parts if p))

        # Batch embed
        embeddings = generate_embeddings_batch(texts)

        for article, emb in zip(articles, embeddings):
            article.embedding = emb

        session.commit()
        logger.info("Embedded %d articles", len(articles))
        return len(articles)


# ──────────────────────────────────────────────── Similarity Search (RAG)

def find_similar_articles(
    query_text: str,
    limit: int = 10,
    language: Optional[str] = None,
    similarity_threshold: float = 0.40,
    hours_back: Optional[int] = 168,
) -> list[dict]:
    """
    Semantic search: find articles most similar to a query string.

    Uses pgvector's cosine distance operator ( <=> ).

    Args:
        query_text:           Natural language query or article text.
        limit:                Max results to return.
        language:             Filter by language code (optional).
        similarity_threshold: Minimum cosine similarity (0-1).
        hours_back: Restrict search to recently collected articles.

    Returns:
        List of dicts: {id, title, url, source_name, language, summary, full_text, published_at, group_id, similarity}
        ordered by highest similarity first.
    """
    query_embedding = generate_embedding(query_text)

    with get_db_session() as session:
        # pgvector cosine distance: 1 - distance = similarity
        # <=> operator returns cosine distance (0 = identical, 2 = opposite)
        distance_expr = Article.embedding.cosine_distance(query_embedding)

        stmt = (
            select(
                Article.id,
                Article.title,
                Article.url,
                Article.source_name,
                Article.language,
                Article.summary,
                Article.full_text,
                Article.published_at,
                Article.group_id,
                (1 - distance_expr).label("similarity"),
            )
            .where(Article.embedding.isnot(None))
        )

        if language:
            stmt = stmt.where(Article.language == language)

        if hours_back is not None:
            window_start = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            stmt = stmt.where(Article.collected_at >= window_start)

        stmt = (
            stmt
            .where((1 - distance_expr) >= similarity_threshold)
            .order_by(distance_expr)
            .limit(limit)
        )

        rows = session.execute(stmt).all()

        return [
            {
                "id": row.id,
                "title": row.title,
                "url": row.url,
                "source_name": row.source_name,
                "language": row.language,
                "summary": row.summary,
                "full_text": row.full_text,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "group_id": row.group_id,
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]


def find_similar_by_article_id(
    article_id: int,
    limit: int = 10,
    similarity_threshold: float = 0.70,
    hours_back: Optional[int] = 168,
) -> list[dict]:
    """
    Find articles semantically similar to an existing article.

    Useful for Level 3 semantic dedup and for grouping related stories.
    """
    with get_db_session() as session:
        article = session.get(Article, article_id)
        if article is None or article.embedding is None:
            return []

        query_emb = article.embedding
        distance_expr = Article.embedding.cosine_distance(query_emb)

        anchor_time = article.collected_at or datetime.now(timezone.utc)

        stmt = (
            select(
                Article.id,
                Article.title,
                Article.source_name,
                Article.language,
                (1 - distance_expr).label("similarity"),
            )
            .where(Article.embedding.isnot(None))
            .where(Article.id != article_id)              # exclude self
            .where((1 - distance_expr) >= similarity_threshold)
            .order_by(distance_expr)
            .limit(limit)
        )

        if hours_back is not None:
            window_start = anchor_time - timedelta(hours=hours_back)
            stmt = stmt.where(Article.collected_at >= window_start)

        rows = session.execute(stmt).all()
        return [
            {
                "id": row.id,
                "title": row.title,
                "source_name": row.source_name,
                "language": row.language,
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]
