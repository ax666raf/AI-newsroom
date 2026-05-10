from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.ai_processing.llm_client import LocalLLMClient
from backend.ai_processing.prompts import build_qa_prompt
from backend.ai_processing.vector_store import find_similar_articles

logger = logging.getLogger(__name__)

LANGUAGE_LABELS = {
    "en": "English",
    "fr": "French",
    "ar": "Arabic",
}


def _normalize_language(language: str | None) -> str:
    normalized = (language or "en").strip().lower()
    if normalized not in LANGUAGE_LABELS:
        return "en"
    return normalized


def _normalize_history(history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not history:
        return []
    cleaned: list[dict[str, Any]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if role and content:
            cleaned.append({"role": role, "content": content})
    return cleaned


def answer_newsroom_question(
    question: str,
    language: str = "en",
    history: list[dict[str, Any]] | None = None,
    limit: int = 5,
    hours_back: int = 72,
) -> dict[str, Any]:
    selected_language = _normalize_language(language)
    cleaned_question = (question or "").strip()
    cleaned_history = _normalize_history(history)

    print("\n" + "="*40)
    print(f"[QA DEBUG] Question: '{cleaned_question}'")
    print(f"[QA DEBUG] Querying Vector DB -> limit: {limit}, hours_back: {hours_back}")

    sources = find_similar_articles(
        cleaned_question,
        limit=limit,
        hours_back=hours_back,
        similarity_threshold=0.20,
    )

    print(f"[QA DEBUG] Vector DB returned {len(sources)} sources.")
    for i, s in enumerate(sources):
        print(f"  -> [{i+1}] Similarity: {s.get('similarity', 'N/A')} | Title: {s.get('title', 'Unknown')}")

    if not sources:
        print("[QA DEBUG] ERROR: No sources found. Vector DB returned empty. Returning fallback.")
        print("="*40 + "\n")
        return {
            "question": cleaned_question,
            "language": selected_language,
            "answer": "I cannot answer this from the available articles right now.",
            "sources": [],
            "retrieved_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    prompt = build_qa_prompt(
        question=cleaned_question,
        articles=sources,
        language=selected_language,
        history=cleaned_history,
    )

    print("[QA DEBUG] Prompt built successfully. Calling LocalLLMClient...")
    
    try:
        answer = LocalLLMClient().generate(prompt)
        print(f"[QA DEBUG] LLM responded successfully! Length: {len(answer)} chars.")
        print("="*40 + "\n")
    except Exception as e:
        print(f"[QA DEBUG] ERROR: LLM Exception occurred: {str(e)}")
        print("="*40 + "\n")
        logger.exception("Newsroom QA generation failed")
        answer = "I cannot answer this from the available articles right now."

    if not answer.strip():
        answer = "I cannot answer this from the available articles right now."

    return {
        "question": cleaned_question,
        "language": selected_language,
        "answer": answer.strip(),
        "sources": [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "source_name": item.get("source_name"),
                "language": item.get("language"),
                "published_at": item.get("published_at"),
                "similarity": item.get("similarity"),
            }
            for item in sources
        ],
        "retrieved_count": len(sources),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }