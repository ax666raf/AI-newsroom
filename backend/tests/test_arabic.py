# Tests for Arabic normalizer
from backend.collector.arabic_normalizer import normalize_arabic

tests = [
    "ٱلْجَزَائِرُ ــــ تَسْتَعِدُّ لِرَمَضَانَ وتُعلِنُ خُطَطًا جَدِيدَةً.",
    "على حدودِ الجزائِرِ، مسؤولةٌ قالت إنّ بيئةَ المؤسّساتِ ممتازةٌ.",
    "هذا اختبار للّام-ألف: ﻻ وﻷ وﻹ وﻵ داخل النص عن الجزائر اليوم.",
    "الجزائر اليوم"
]

for t in tests:
    out = normalize_arabic(t)
    print("\nIN:   ", t)
    print("OUT:  ", out["text"])
    print("LANG: ", out["language"])