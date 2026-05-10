from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.ai_processing.question_answerer import answer_newsroom_question

router = APIRouter()


class QAHistoryMessage(BaseModel):
    role: str = Field(min_length=1)
    content: str = Field(min_length=1)


class QARequest(BaseModel):
    question: str = Field(min_length=1)
    language: str = Field(default="en", min_length=2, max_length=10)
    limit: int = Field(default=5, ge=1, le=10)
    hours_back: int = Field(default=2160, ge=1, le=8760)
    messages: list[QAHistoryMessage] = Field(default_factory=list)

    @field_validator("question")
    @classmethod
    def _strip_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must not be empty")
        return cleaned

    @field_validator("language")
    @classmethod
    def _normalize_language(cls, value: str) -> str:
        return (value or "en").strip().lower()


def _messages_to_dicts(messages: list[QAHistoryMessage]) -> list[dict[str, Any]]:
    return [{"role": message.role, "content": message.content} for message in messages]


@router.post("")
@router.post("/")
def ask_question(payload: QARequest):
    try:
        return answer_newsroom_question(
            question=payload.question,
            language=payload.language,
            history=_messages_to_dicts(payload.messages),
            limit=payload.limit,
            hours_back=payload.hours_back,
        )
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unable to answer question: {str(exc)}") from exc