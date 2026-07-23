"""DART0s hard-fail detector.

Scoring was removed. Only hard-fail keyword detection remains.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class HardFailResult:
    detected: bool
    matched_keyword: Optional[str] = None
    skip_llm: bool = True


# ---------------------------------------------------------------------------
# Hard-fail keywords
# ---------------------------------------------------------------------------

HARD_FAIL_KEYWORDS = [
    "감사의견거절",
    "감사의견한정",
    "감사의견부적정",
    "횡령",
    "배임",
    "감자",
    "상장폐지",
]


def check_hard_fail(raw_text: str) -> HardFailResult:
    for kw in HARD_FAIL_KEYWORDS:
        if kw in raw_text:
            return HardFailResult(
                detected=True,
                matched_keyword=kw,
            )
    return HardFailResult(detected=False)
