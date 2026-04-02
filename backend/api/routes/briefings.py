from fastapi import APIRouter, Query

from backend.briefing.assembler import get_or_create_today_briefing

router = APIRouter()


@router.get("/today")
def get_today_briefing(language: str = Query(default="en", min_length=2, max_length=10)):
    """Return today's assembled briefing in the requested language."""
    selected_language = (language or "en").strip().lower()
    return get_or_create_today_briefing(language=selected_language)
