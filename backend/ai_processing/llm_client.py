"""llm_client.py - LLM client using Mistral API."""

from __future__ import annotations

import logging
import os

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Mistral API configuration
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_BASE_URL = "https://api.mistral.ai/v1"
MODEL_NAME = os.getenv("LLM_MODEL", "mistral-medium")
TEMPERATURE = 0.1  # lower temp for strict JSON output


class LocalLLMClient:
    """LLM client configured for newsroom briefing generation via Mistral API."""

    def __init__(self) -> None:
        if not MISTRAL_API_KEY:
            raise ValueError("MISTRAL_API_KEY not set in environment")
        self.api_key = MISTRAL_API_KEY
        self.endpoint = f"{MISTRAL_BASE_URL}/messages"
        self.model = MODEL_NAME

    def generate(self, prompt: str) -> str:
        """Generate content from Mistral API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": TEMPERATURE,#randomness
            "max_tokens": 1000,#limit so that response not too long
        }

        try:
            response = requests.post(self.endpoint, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            # Mistral returns messages with content in choices array
            return data["choices"][0]["message"]["content"].strip()
        except requests.RequestException as exc:
            logger.error("Mistral API request failed: %s", exc)
            raise
