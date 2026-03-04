# Arabic Normalizer module
# backend/collector/arabic_normalizer.py
from __future__ import annotations

import re
import unicodedata
from typing import Dict

from langdetect import detect, LangDetectException

_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_TATWEEL_RE = re.compile(r"\u0640+")
_WS_RE = re.compile(r"\s+")

# Lam-Alef ligatures -> "لا"
_LAMALEF_MAP = {
    "\ufefb": "لا",  # ﻻ
    "\ufef7": "لا",  # ﻷ
    "\ufef9": "لا",  # ﻹ
    "\ufef5": "لا",  # ﻵ
}

_ALEF_MAP = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"}

# Mild hamza normalization for matching (keep standalone hamza "ء" to preserve text)
_HAMZA_MILD_MAP = {"ؤ": "و", "ئ": "ي"}


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def remove_diacritics(text: str) -> str:
    return _DIACRITICS_RE.sub("", text)


def remove_tatweel(text: str) -> str:
    return _TATWEEL_RE.sub("", text)


def normalize_lamalef(text: str) -> str:
    for k, v in _LAMALEF_MAP.items():
        text = text.replace(k, v)
    return text


def standardize_alef(text: str) -> str:
    for k, v in _ALEF_MAP.items():
        text = text.replace(k, v)
    return text


def standardize_yeh(text: str) -> str:
    return text.replace("ى", "ي")


def standardize_teh_marbuta(text: str) -> str:
    # combined mode: convert ة -> ه for stronger matching
    return text.replace("ة", "ه")


def normalize_hamza_mild(text: str) -> str:
    for k, v in _HAMZA_MILD_MAP.items():
        text = text.replace(k, v)
    return text


def clean_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def detect_language(text: str) -> str:
    if not text:
        return "unknown"
    s = text.strip()
    if len(s) < 30:
        return "unknown"
    try:
        return detect(s)
    except (LangDetectException, Exception):
        return "unknown"


def normalize_arabic(text: str | None, do_lang_detect: bool = True) -> Dict[str, str]:
    """
    Single combined Arabic normalization mode:
    - NFC unicode
    - remove tatweel
    - remove diacritics
    - normalize lam-alef ligatures
    - normalize alef variants
    - normalize ى -> ي
    - normalize ة -> ه
    - normalize mild hamza: ؤ -> و, ئ -> ي
    - whitespace cleanup
    - optional language detect
    """
    if text is None:
        text = ""

    t = normalize_unicode(text)
    t = remove_tatweel(t)
    t = remove_diacritics(t)
    t = normalize_lamalef(t)
    t = standardize_alef(t)
    t = standardize_yeh(t)
    t = standardize_teh_marbuta(t)
    t = normalize_hamza_mild(t)
    t = clean_whitespace(t)

    lang = detect_language(t) if do_lang_detect else "unknown"
    return {"text": t, "language": lang}