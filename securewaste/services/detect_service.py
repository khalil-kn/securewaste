"""Text-detection service for the /detect page (Issue #5).

Runs the detection engine over a single block of pasted text and returns the findings plus a
masked copy of the text (the original is never echoed back to the page). This keeps the route
thin and puts the engine wiring in one place. It does not persist anything (persistence is
Milestone 3).
"""

from __future__ import annotations

from securewaste.core.detection.engine import DetectionEngine, mask_text
from securewaste.core.detection.rules.email import EmailRule
from securewaste.core.detection.rules.keywords import KeywordRule
from securewaste.core.detection.rules.phone import PhoneRule
from securewaste.core.extraction import PageText


def _build_rules(keywords: list[str]):
    rules = [EmailRule(), PhoneRule()]
    if keywords:
        rules.append(KeywordRule(keywords))
    return rules


def detect_text(text: str, keywords: list[str], min_confidence: float, hmac_key: bytes) -> tuple[list, str]:
    """Return (findings, masked_text). masked_text has every detected value replaced by its mask."""
    rules = _build_rules(keywords)
    engine = DetectionEngine(rules, min_confidence, hmac_key)
    findings = engine.scan([PageText(page_number=1, text=text)])
    return findings, mask_text(text, rules)
