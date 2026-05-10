from __future__ import annotations

from pydantic import ValidationError
from unittest.mock import patch

from backend.api.routes.qa import QARequest, ask_question


def test_qa_endpoint_returns_expected_payload():
    mock_response = {
        "question": "What changed in the budget?",
        "language": "en",
        "answer": "The budget update was significant [1].",
        "sources": [
            {
                "title": "Budget update",
                "url": "https://example.com/a1",
                "source_name": "Example News",
                "language": "en",
                "published_at": "2026-04-29T10:00:00+00:00",
                "similarity": 0.91,
            }
        ],
        "retrieved_count": 1,
        "timestamp": "2026-04-29T11:41:21.923370+00:00",
    }

    with patch("backend.api.routes.qa.answer_newsroom_question", return_value=mock_response):
        payload = ask_question(
            QARequest(
                question="What changed in the budget?",
                language="en",
                limit=5,
                hours_back=72,
                messages=[
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello"},
                ],
            )
        )

    assert payload["question"] == "What changed in the budget?"
    assert payload["language"] == "en"
    assert payload["answer"]
    assert payload["retrieved_count"] == 1
    assert payload["sources"]
    assert payload["timestamp"]


def test_qa_endpoint_rejects_empty_question():
    try:
        QARequest(question="", language="en", messages=[])
        raise AssertionError("Expected ValidationError")
    except ValidationError:
        assert True