"""
arabic_normalizer.py — Unicode normalisation for Arabic text.

Algerian news sources mix several Arabic orthographic conventions:
  • Different forms of Alef (أ إ آ ا)
  • Teh Marbuta (ة) vs Heh (ه)
  • Yeh (ي) vs Alef Maksura (ى)
  • Tatweel / Kashida decoration (ـ)
  • Diacritics (harakat تشكيل)

Normalising these ensures deduplication works correctly even when
two sources write the same word differently.
"""

import re
import unicodedata

# Map variant Alef forms → plain Alef
_ALEF_VARIANTS = str.maketrans({
    "\u0623": "\u0627",  # أ → ا
    "\u0625": "\u0627",  # إ → ا
    "\u0622": "\u0627",  # آ → ا
    "\u0671": "\u0627",  # ٱ → ا
})

# Arabic diacritics (short vowels / tanwin) — strip for comparison
_DIACRITICS_PATTERN = re.compile(
    r"[\u064B-\u065F\u0670]"
)

# Tatweel / Kashida elongation mark
_TATWEEL = "\u0640"


def normalize_arabic(text: str) -> str:
    """
    Normalise Arabic text for storage and comparison.

    Steps:
      1. Unicode NFC normalisation
      2. Remove tatweel (decorative elongation)
      3. Remove diacritics (harakat)
      4. Unify Alef variants
      5. Normalise Teh Marbuta → Heh  (for dedup only; stored as-is)
      6. Normalise Yeh / Alef Maksura
      7. Collapse multiple whitespace
    """
    if not text:
        return text

    text = unicodedata.normalize("NFC", text)
    text = text.replace(_TATWEEL, "")
    text = _DIACRITICS_PATTERN.sub("", text)
    text = text.translate(_ALEF_VARIANTS)
    # Teh Marbuta → Heh (helps dedup across dialects)
    text = text.replace("\u0629", "\u0647")  # ة → ه
    # Alef Maksura → Yeh
    text = text.replace("\u0649", "\u064A")  # ى → ي
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_for_dedup(text: str) -> str:
    """
    Aggressive normalisation used only for duplicate detection.
    Lower-cases Latin portions and strips all punctuation.
    """
    text = normalize_arabic(text)
    text = re.sub(r"[^\w\s\u0600-\u06FF]", "", text, flags=re.UNICODE)
    return text.lower().strip()
