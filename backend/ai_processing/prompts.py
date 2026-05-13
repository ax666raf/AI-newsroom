"""prompts.py - Prompt builders for newsroom briefing generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _first_500_chars(value: str | None) -> str:
    text = (value or "").strip()
    return text[:500]


def _format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if value is None:
        return "unknown"
    return str(value)


def _language_name(language: str) -> str:
    normalized = (language or "en").strip().lower()
    if normalized == "fr":
        return "French"
    if normalized == "ar":
        return "Arabic"
    return "English"


def build_story_group_prompt(
    output_language: str,
    todays_articles: list[dict[str, Any]],
    historical_background: list[dict[str, Any]],
) -> str:
    """Build a strict JSON prompt for summarizing one story group."""
    lines: list[str] = []

    allowed_categories = "World, Politics, Economy, Business, Technology, Science, Health, Sports, Culture"
    allowed_sentiments = "positive, neutral, negative, mixed"

    # First line must explicitly state output language.
    lines.append(f"Output language: {output_language}") #tells mistral what language the output should be
    lines.append("")
    lines.append("You are an AI news editor. Use the data below to produce one balanced newsroom item.")
    lines.append("")

    lines.append("Today's articles:")
    if todays_articles: #add the articles
        for idx, article in enumerate(todays_articles, start=1):
            source = article.get("source_name") or article.get("source") or "unknown"
            language = article.get("language") or "unknown"
            title = article.get("title") or ""
            snippet = _first_500_chars(article.get("full_text") or article.get("summary") or "")
            lines.append(f"{idx}. source: {source}")
            lines.append(f"   language: {language}")
            lines.append(f"   title: {title}")
            lines.append(f"   first_500_chars: {snippet}")
    else:
        lines.append("none")
    lines.append("")

    lines.append("Historical background:")
    if historical_background: #old articles for background
        for idx, article in enumerate(historical_background, start=1):
            date_str = _format_date(article.get("published_at") or article.get("date"))
            source = article.get("source_name") or article.get("source") or "unknown"
            title = article.get("title") or ""
            summary = article.get("summary") or ""
            lines.append(f"{idx}. date: {date_str}")
            lines.append(f"   source: {source}")
            lines.append(f"   title: {title}")
            lines.append(f"   summary: {summary}")
    else:
        lines.append("none")
    lines.append("")

    lines.append("Instructions:")
    lines.append("- Write summary using exactly three sentences.")
    lines.append("- Keep wording neutral and factual.")
    lines.append("- Use historical background only when relevant and mention whether context was used.")
    lines.append(f"- Choose category from: {allowed_categories}.")
    lines.append(f"- Choose sentiment from: {allowed_sentiments}.")
    lines.append("- Return flat scalar values only: no nested objects, no arrays, no extra keys.")
    lines.append("")

    lines.append("Return JSON with exactly these fields:")
    lines.append("neutral_headline, summary, why_it_matters, category, sentiment, context_used")
    lines.append("Use double quotes for all JSON strings, and return only valid JSON, no markdown, no code fences.")

    return "\n".join(lines)


def build_qa_prompt(
    question: str,
    articles: list[dict[str, Any]],
    language: str = "en",
    history: list[dict[str, Any]] | None = None,
) -> str:
    lines: list[str] = []
    output_language = _language_name(language)
    current_date = datetime.now().strftime("%B %d, %Y")

    lines.append(f"System Date: {current_date}")
    lines.append(f"Output language: {output_language}")
    lines.append("")
    lines.append("You are a newsroom Q&A assistant. Answer only from the provided newsroom articles and conversation context.")
    lines.append("")
    lines.append(f"Question: {question.strip()}")
    lines.append("")

    if history:
        lines.append("Conversation context:")
        for idx, message in enumerate(history[-6:], start=1):
            role = str(message.get("role") or "message").strip().lower()
            content = _first_500_chars(str(message.get("content") or ""))
            if content:
                lines.append(f"{idx}. {role}: {content}")
        lines.append("")

    lines.append("Newsroom articles:")
    if articles:
        for idx, article in enumerate(articles, start=1):
            title = article.get("title") or "Untitled"
            source = article.get("source_name") or article.get("source") or "unknown"
            url = article.get("url") or ""
            published_at = _format_date(article.get("published_at") or article.get("collected_at"))
            article_language = article.get("language") or "unknown"
            summary = _first_500_chars(article.get("summary") or "")
            excerpt = _first_500_chars(article.get("full_text") or "")

            lines.append(f"[{idx}] title: {title}")
            lines.append(f"    source: {source}")
            lines.append(f"    url: {url}")
            lines.append(f"    published_at: {published_at}")
            lines.append(f"    language: {article_language}")
            if summary:
                lines.append(f"    summary: {summary}")
            if excerpt:
                lines.append(f"    excerpt: {excerpt}")
    else:
        lines.append("none")
    lines.append("")

    lines.append("Instructions:")
    lines.append("- Answer in plain prose, not JSON.")
    lines.append("- Use only the listed articles and conversation context.")
    lines.append("- Cite facts inline with bracketed numbers like [1], [2].")
    lines.append("- If the articles do not support an answer, say you cannot answer from the available articles.")
    lines.append("- Write the final answer in  : if the user talked in a specific language without specifying the language,  reply with the user language, else, reply with the desired language from the user question.")
    lines.append("- Keep the response concise, factual, and newsroom-appropriate.")
    lines.append("")
    lines.append("Return only the answer text.")

    return "\n".join(lines)
