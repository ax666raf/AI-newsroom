"""gemini_client.py - Thin Gemini wrapper with retries and pacing."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
import google.generativeai as genai

logger = logging.getLogger(__name__)

MODEL_NAME = "models/gemini-2.0-flash"
TEMPERATURE = 0.3
MAX_OUTPUT_TOKENS = 1000
RATE_LIMIT_BACKOFF_SECONDS = [60, 120, 180]
POST_SUCCESS_DELAY_SECONDS = 4


def _load_api_key() -> str:
    """Load GEMINI_API_KEY from backend/.env using python-dotenv."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in backend/.env")
    return api_key


def _is_rate_limit_error(exc: Exception) -> bool:
    """Best-effort detection for Gemini 429/rate limit responses."""
    status_code = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    if status_code == 429 or code == 429:
        return True

    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "resource_exhausted" in text


class GeminiClient:
    """Gemini client configured for newsroom briefing generation."""

    def __init__(self) -> None:
        api_key = _load_api_key()
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(MODEL_NAME)

    def generate(self, prompt: str) -> str:
        """
        Generate content from Gemini.

        Retries up to 3 times for 429 errors, waiting 60/120/180 seconds.
        Sleeps 4 seconds after each successful call to stay within free-tier limits.
        """
        for attempt, wait_seconds in enumerate(RATE_LIMIT_BACKOFF_SECONDS, start=1):
            try:
                response = self._model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=TEMPERATURE,
                        max_output_tokens=MAX_OUTPUT_TOKENS,
                    ),
                )

                text = (response.text or "").strip()
                time.sleep(POST_SUCCESS_DELAY_SECONDS)
                return text

            except Exception as exc:  # noqa: BLE001
                if _is_rate_limit_error(exc):
                    logger.warning(
                        "Gemini rate limited (attempt %d/3). Retrying in %ds",
                        attempt,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue
                raise

        # Final attempt after completing all scheduled backoffs.
        response = self._model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=TEMPERATURE,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )
        text = (response.text or "").strip()
        time.sleep(POST_SUCCESS_DELAY_SECONDS)
        return text
