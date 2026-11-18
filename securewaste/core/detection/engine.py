"""Detection engine (FR-08 → FR-13). Owner: Milestone 1 issue #5.

The engine runs every rule on every page, drops candidates below the confidence floor, masks
each value (so the real value never leaves detection), merges duplicates of the same detected
value on the same page, and returns a list of Finding objects.

Masking is applied to the whole page text up front, so every context window is guaranteed to
hide every detected value — not just the finding's own value (ST-01 / ST-02).

Two details keep that guarantee honest:
  * Masking changes the text length ("alice.secret@example.com" -> "a•••@e•••.com"), so the
    finding's original offsets are translated into masked-text coordinates before cutting the
    window. Cutting with the original offsets shifted the window and cut words in half.
  * The window is also scrubbed for anything that LOOKS sensitive (e-mail, phone-like numbers)
    but that no rule detected, so an undetected value can never appear in a context box.
"""

from __future__ import annotations

import re

from securewaste.core.detection.catalogue import CATALOGUE, Category
from securewaste.core.detection.masking import mask, value_hmac
from securewaste.core.detection.models import Finding
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText

_CONTEXT_MARGIN = 30

# Safety net for values no rule detected (the bullet is excluded so masks are never re-masked).
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_DIGIT_RUN_RE = re.compile(r"(?<![\w\u2022])\+?\(?\d[\d\s().\-]{6,}\d(?![\w\u2022])")
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def mask_text(text: str, rules: list[DetectionRule]) -> str:
    """Return *text* with every value detected by *rules* replaced by its mask."""
    page = PageText(page_number=1, text=text)
    candidates = [candidate for rule in rules for candidate in rule.find(page)]
    return _mask_page(text, candidates)[0]


class DetectionEngine:
    def __init__(self, rules: list[DetectionRule], min_confidence: float, hmac_key: bytes):
        self.rules = rules
        self.min_confidence = min_confidence
        self.hmac_key = hmac_key

    def scan(self, pages: list[PageText]) -> list[Finding]:
        findings: list[Finding] = []
        by_fingerprint: dict[tuple, Finding] = {}

        for page in pages:
            candidates = [candidate for rule in self.rules for candidate in rule.find(page)]
            masked_text, mapping = _mask_page(page.text, candidates)

            for candidate in candidates:
                if candidate.confidence < self.min_confidence:
                    continue

                info = CATALOGUE[candidate.category]
                fingerprint = value_hmac(self.hmac_key, candidate.rule_id, candidate.raw_value)
                key = (candidate.rule_id, candidate.category, page.page_number, fingerprint)

                existing = by_fingerprint.get(key)
                if existing is not None:
                    existing.occurrences += 1
                    continue

                ctx_start = _translate(mapping, candidate.char_start, is_end=False)
                ctx_end = _translate(mapping, candidate.char_end, is_end=True)

                finding = Finding(
                    rule_id=candidate.rule_id,
                    category=candidate.category,
                    severity=info.severity,
                    confidence=candidate.confidence,
                    page_number=candidate.page_number,
                    char_start=candidate.char_start,
                    char_end=candidate.char_end,
                    masked_value=mask(candidate.category, candidate.raw_value),
                    value_hmac=fingerprint,
                    context=_context_window(masked_text, ctx_start, ctx_end),
                    explanation=info.explanation,
                    recommendation=info.recommendation,
                    occurrences=1,
                    validation=candidate.validation,
                )
                findings.append(finding)
                by_fingerprint[key] = finding

        return findings


# ---------------------------------------------------------------- masking --
def _spans(text: str, candidates) -> list[tuple[int, int, Category]]:
    """Every range to mask: each candidate's own range plus every other occurrence of its value."""
    raw: list[tuple[int, int, Category]] = []
    for c in candidates:
        if 0 <= c.char_start < c.char_end <= len(text):
            raw.append((c.char_start, c.char_end, c.category))
        if c.raw_value:
            i = text.find(c.raw_value)
            while i != -1:
                raw.append((i, i + len(c.raw_value), c.category))
                i = text.find(c.raw_value, i + 1)

    raw.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    merged: list[tuple[int, int, Category]] = []
    for start, end, category in raw:
        if merged and start < merged[-1][1]:  # overlaps the previous range: extend it
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end, merged[-1][2])
        else:
            merged.append((start, end, category))
    return merged


def _mask_page(text: str, candidates) -> tuple[str, list[tuple[int, int, int, int]]]:
    """Return (masked text, mapping) where mapping rows are (orig_start, orig_end, masked_start, masked_end)."""
    pieces: list[str] = []
    mapping: list[tuple[int, int, int, int]] = []
    pos = 0
    out_len = 0
    for start, end, category in _spans(text, candidates):
        pieces.append(text[pos:start])
        out_len += start - pos
        masked = mask(category, text[start:end])
        mapping.append((start, end, out_len, out_len + len(masked)))
        pieces.append(masked)
        out_len += len(masked)
        pos = end
    pieces.append(text[pos:])
    return "".join(pieces), mapping


def _translate(mapping: list[tuple[int, int, int, int]], pos: int, *, is_end: bool) -> int:
    """Convert a position in the ORIGINAL text into the matching position in the MASKED text."""
    delta = 0
    for start, end, masked_start, masked_end in mapping:
        if pos >= end:
            delta = masked_end - end
            continue
        if pos < start or (is_end and pos == start):
            break
        return masked_end if is_end else masked_start  # inside a masked value
    return pos + delta


# ---------------------------------------------------------------- context --
def _context_window(masked_text: str, start: int, end: int) -> str:
    """A ±30-character window of the already-masked text, cut on word boundaries and scrubbed."""
    lo = max(0, start - _CONTEXT_MARGIN)
    hi = min(len(masked_text), end + _CONTEXT_MARGIN)

    while 0 < lo < start and not masked_text[lo - 1].isspace():  # don't start mid-word
        lo += 1
    while end < hi < len(masked_text) and not masked_text[hi].isspace():  # don't end mid-word
        hi -= 1

    window = " ".join(masked_text[lo:hi].split())
    return _scrub_unrecognised(window)


def _scrub_unrecognised(text: str) -> str:
    """Mask e-mail addresses and phone-like numbers that no rule detected (defence in depth)."""
    text = _EMAIL_RE.sub(lambda m: mask(Category.EMAIL, m.group()), text)

    def _digits(match: re.Match) -> str:
        run = match.group()
        digits = sum(ch.isdigit() for ch in run)
        if not 8 <= digits <= 19 or _ISO_DATE_RE.fullmatch(run.strip()):
            return run
        return mask(Category.PHONE, run)

    return _DIGIT_RUN_RE.sub(_digits, text)