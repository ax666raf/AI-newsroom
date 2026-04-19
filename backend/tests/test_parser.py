import json

import pytest

from backend.ai_processing.parser import (
    build_minimal_valid_object,
    extract_json_substring,
    normalize_payload,
    parse_gemini_response,
    safe_process,
    strip_markdown_fences,
)


def _valid_payload(**overrides):
    payload = {
        "neutral_headline": "Algeria policy update",
        "summary": "A summary.",
        "why_it_matters": "A reason.",
        "category": "World",
        "sentiment": "neutral",
        "context_used": False,
    }
    payload.update(overrides)
    return payload


def test_build_minimal_valid_object_uses_trimmed_fallback_headline():
    out = build_minimal_valid_object("  Breaking update  ")
    assert out["neutral_headline"] == "Breaking update"
    assert out["category"] == "World"
    assert out["sentiment"] == "neutral"
    assert out["context_used"] is False


def test_strip_markdown_fences_extracts_inner_json_text():
    raw = """```json
    {\n  \"a\": 1\n}
    ```"""
    cleaned = strip_markdown_fences(raw)
    assert cleaned == '{\n  "a": 1\n}'


def test_extract_json_substring_returns_first_object_slice():
    text = "model output: {\"k\":\"v\"} trailing explanation"
    assert extract_json_substring(text) == '{"k":"v"}'


def test_normalize_payload_maps_aliases_and_coerces_values():
    payload = _valid_payload(
        neutral_headline="  Headline  ",
        summary=["part 1", "", "part 2"],
        why_it_matters="  Why now  ",
        category="business",
        sentiment="MIXED",
        context_used="yes",
    )

    normalized = normalize_payload(payload)

    assert normalized["neutral_headline"] == "Headline"
    assert normalized["summary"] == "part 1 part 2"
    assert normalized["why_it_matters"] == "Why now"
    assert normalized["category"] == "Economy"
    assert normalized["sentiment"] == "neutral"
    assert normalized["context_used"] is True


def test_normalize_payload_supports_camel_case_keys():
    payload = {
        "neutralHeadline": "Title",
        "summary": "Summary",
        "whyItMatters": "Because",
        "category": "politics",
        "sentiment": "positive",
        "contextUsed": "0",
    }

    normalized = normalize_payload(payload)

    assert normalized["neutral_headline"] == "Title"
    assert normalized["why_it_matters"] == "Because"
    assert normalized["category"] == "Politics"
    assert normalized["sentiment"] == "positive"
    assert normalized["context_used"] is False


def test_parse_gemini_response_accepts_fenced_json_and_normalizes():
    raw = "```json\n" + json.dumps(_valid_payload(category="sport")) + "\n```"
    out = parse_gemini_response(raw)
    assert out["category"] == "Sports"


def test_parse_gemini_response_falls_back_to_extracted_json_substring():
    body = json.dumps(_valid_payload(sentiment="balanced", context_used=1))
    raw = f"some intro text\n{body}\nextra footer"

    out = parse_gemini_response(raw)

    assert out["sentiment"] == "neutral"
    assert out["context_used"] is True


def test_parse_gemini_response_raises_on_invalid_payload():
    with pytest.raises(ValueError):
        parse_gemini_response("not json here")


def test_normalize_payload_raises_when_required_field_missing():
    payload = _valid_payload()
    payload.pop("summary")

    with pytest.raises(ValueError, match="Missing required fields"):
        normalize_payload(payload)


def test_safe_process_never_raises_and_returns_fallback_object():
    out = safe_process("bad response", fallback_headline="Fallback title")
    assert out["neutral_headline"] == "Fallback title"
    assert out["summary"] == "No reliable summary was generated."
    assert out["category"] == "World"
    assert out["sentiment"] == "neutral"
    assert out["context_used"] is False