"""
semantic_match.py — Level 3 Deduplication + Story Grouping.

After Level 1 (URL hash) and Level 2 (fuzzy title), this module uses
vector embeddings to:

  1. Catch cross-language duplicates
     (e.g. same story in Arabic + French + English)
  2. Group related articles into StoryGroups
     (different articles covering the same event)

Algorithm:
  - For each new article with an embedding, find existing articles
    with cosine similarity ≥ threshold.
  - If matches found → assign to the same StoryGroup.
  - If no matches → create a new StoryGroup.
  - Update coverage_count, source_names, languages on the group.
"""

import logging
from typing import Optional

import numpy as np
from sqlalchemy import select, func

from backend.database.db import get_db_session
from backend.database.models import Article, StoryGroup
from backend.ai_processing.vector_store import (
    find_similar_by_article_id,
    generate_embedding,
)

logger = logging.getLogger(__name__)

# Cosine similarity threshold for considering two articles the "same story"
# 0.75 is conservative — same event reported differently
GROUP_SIMILARITY_THRESHOLD = 0.75


def assign_article_to_group(article_id: int) -> Optional[int]:
    """
    Assign a single article to an existing or new StoryGroup based on
    semantic similarity.

    Returns:
        The StoryGroup.id the article was assigned to, or None on failure.
    """
    with get_db_session() as session:
        article = session.get(Article, article_id)
        if article is None:
            logger.warning("Article %d not found", article_id)
            return None

        if article.group_id is not None:
            logger.debug("Article %d already in group %d", article_id, article.group_id)
            return article.group_id

        if article.embedding is None:
            logger.warning("Article %d has no embedding — cannot group", article_id)
            return None

        # Find semantically similar articles that are already grouped
        similar = find_similar_by_article_id(
            article_id,
            limit=5,
            similarity_threshold=GROUP_SIMILARITY_THRESHOLD,
        )

        # Try to find an existing group from the similar articles
        target_group_id = None
        for match in similar:
            matched = session.get(Article, match["id"])
            if matched and matched.group_id is not None:
                target_group_id = matched.group_id
                break

        if target_group_id is not None:
            # ── Add to existing group
            group = session.get(StoryGroup, target_group_id)
            article.group_id = target_group_id

            group.coverage_count = (group.coverage_count or 0) + 1

            # Update source_names list (avoid duplicates)
            current_sources = set(group.source_names or [])
            current_sources.add(article.source_name)
            group.source_names = list(current_sources)

            # Update languages list
            current_langs = set(group.languages or [])
            current_langs.add(article.language)
            group.languages = list(current_langs)

            session.commit()
            logger.info(
                "Article %d → existing group %d (coverage=%d)",
                article_id, group.id, group.coverage_count,
            )
            return group.id

        else:
            # ── Create a new StoryGroup
            group = StoryGroup(
                primary_title=article.title,
                category=article.category,
                coverage_count=1,
                source_names=[article.source_name],
                languages=[article.language],
                region=article.region or "algeria",
                representative_embedding=article.embedding,
            )
            session.add(group)
            session.flush()  # get group.id

            article.group_id = group.id

            # Also assign the similar (ungrouped) articles to this new group
            for match in similar:
                matched = session.get(Article, match["id"])
                if matched and matched.group_id is None:
                    matched.group_id = group.id
                    group.coverage_count += 1
                    sources = set(group.source_names or [])
                    sources.add(matched.source_name)
                    group.source_names = list(sources)
                    langs = set(group.languages or [])
                    langs.add(matched.language)
                    group.languages = list(langs)

            session.commit()
            logger.info(
                "Article %d → NEW group %d (coverage=%d)",
                article_id, group.id, group.coverage_count,
            )
            return group.id


def group_unprocessed_articles(limit: int = 200) -> dict:
    """
    Find articles that have embeddings but no group_id, and assign them.

    Returns:
        Summary dict {processed, groups_created, groups_extended}
    """
    with get_db_session() as session:
        stmt = (
            select(Article.id)
            .where(Article.embedding.isnot(None))
            .where(Article.group_id.is_(None))
            .order_by(Article.collected_at.desc())
            .limit(limit)
        )
        article_ids = [row[0] for row in session.execute(stmt)]

    if not article_ids:
        logger.info("No ungrouped articles to process")
        return {"processed": 0, "groups_created": 0, "groups_extended": 0}

    logger.info("Grouping %d ungrouped articles ...", len(article_ids))

    # Count groups before
    with get_db_session() as session:
        groups_before = session.scalar(select(func.count(StoryGroup.id)))

    # Process each article
    processed = 0
    for aid in article_ids:
        result = assign_article_to_group(aid)
        if result is not None:
            processed += 1

    # Count groups after
    with get_db_session() as session:
        groups_after = session.scalar(select(func.count(StoryGroup.id)))

    groups_created = groups_after - groups_before

    summary = {
        "processed": processed,
        "groups_created": groups_created,
        "groups_extended": processed - groups_created,
    }
    logger.info("Grouping complete: %s", summary)
    return summary


def update_group_representative_embedding(group_id: int) -> bool:
    """
    Recompute the representative (centroid) embedding for a StoryGroup.

    Called after articles are added/removed from a group.
    The centroid is the average of all member article embeddings.
    """
    with get_db_session() as session:
        group = session.get(StoryGroup, group_id)
        if group is None:
            return False

        stmt = (
            select(Article.embedding)
            .where(Article.group_id == group_id)
            .where(Article.embedding.isnot(None))
        )
        embeddings = [row[0] for row in session.execute(stmt)]

        if not embeddings:
            return False

        # Compute centroid
        centroid = np.mean(embeddings, axis=0)
        # Normalise to unit vector
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm

        group.representative_embedding = centroid.tolist()
        session.commit()
        logger.debug("Updated centroid for group %d (%d articles)", group_id, len(embeddings))
        return True
