from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.config import DATABASE_URL
from backend.database.db import get_db_session, init_db
from backend.database.models import Article, StoryGroup
from backend.deduplication.fuzzy_match import are_titles_similar
from backend.deduplication.semantic_match import assign_article_to_group
from backend.deduplication.url_hash import compute_url_hash


def test_url_hash_uses_md5_32_chars():
	h = compute_url_hash(" https://Example.com/News/123/ ")
	assert len(h) == 32
	assert h == compute_url_hash("https://example.com/news/123")


def test_fuzzy_threshold_75():
	title_a = "Algeria signs new gas deal with Italy"
	title_b = "Algeria signs gas deal with Italy"
	assert are_titles_similar(title_a, title_b, threshold=75)


@pytest.mark.integration
def test_cross_language_story_groups_into_one_cluster():
	if not DATABASE_URL:
		pytest.skip("DATABASE_URL not configured")

	init_db()

	stamp = uuid4().hex[:10]
	shared_vec = [0.0] * 384
	shared_vec[0] = 1.0

	with get_db_session() as session:
		a1 = Article(
			title="الرئيس تبون يعلن خطة اقتصادية جديدة",
			url=f"https://example.com/{stamp}/ar",
			url_hash=compute_url_hash(f"https://example.com/{stamp}/ar"),
			summary="خطة اقتصادية جديدة في الجزائر",
			source_name="Arabic Source",
			language="ar",
			region="algeria",
			category="economy",
			published_at=datetime.now(timezone.utc),
			embedding=shared_vec,
		)
		a2 = Article(
			title="Tebboune annonce un nouveau plan economique",
			url=f"https://example.com/{stamp}/fr",
			url_hash=compute_url_hash(f"https://example.com/{stamp}/fr"),
			summary="Nouveau plan economique en Algerie",
			source_name="French Source",
			language="fr",
			region="algeria",
			category="economy",
			published_at=datetime.now(timezone.utc),
			embedding=shared_vec,
		)
		a3 = Article(
			title="Algeria unveils a new economic roadmap",
			url=f"https://example.com/{stamp}/en",
			url_hash=compute_url_hash(f"https://example.com/{stamp}/en"),
			summary="New economic roadmap announced in Algeria",
			source_name="English Source",
			language="en",
			region="algeria",
			category="economy",
			published_at=datetime.now(timezone.utc),
			embedding=shared_vec,
		)
		session.add_all([a1, a2, a3])
		session.flush()
		ids = [a1.id, a2.id, a3.id]
		session.commit()

	try:
		for aid in ids:
			assert assign_article_to_group(aid) is not None

		with get_db_session() as session:
			grouped = session.query(Article).filter(Article.id.in_(ids)).all()
			group_ids = {a.group_id for a in grouped}
			assert len(group_ids) == 1
			group_id = next(iter(group_ids))
			assert group_id is not None

			group = session.get(StoryGroup, group_id)
			assert group is not None
			assert group.coverage_count >= 3
			assert {"ar", "fr", "en"}.issubset(set(group.languages or []))
			assert {
				"Arabic Source",
				"French Source",
				"English Source",
			}.issubset(set(group.source_names or []))
	finally:
		with get_db_session() as session:
			session.query(Article).filter(Article.id.in_(ids)).delete(synchronize_session=False)
			session.query(StoryGroup).filter(StoryGroup.primary_title.in_([
				"الرئيس تبون يعلن خطة اقتصادية جديدة",
				"Tebboune annonce un nouveau plan economique",
				"Algeria unveils a new economic roadmap",
			])).delete(synchronize_session=False)
			session.commit()
