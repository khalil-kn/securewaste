"""Masking and keyed hashing (FR-13, ADR-0006). Owner: Milestone 1 issue #5.

mask(category, value)        -> "•••• •••• •••• 4242", "s•••@e•••.tn", "AKIA••••••••"
value_hmac(key, rule_id, v)  -> HMAC-SHA256 hex of rule_id + normalised value (use hmac + hashlib)
"""

from __future__ import annotations

import hashlib
import hmac
import re

from securewaste.core.detection.catalogue import Category

_BULLET = "•••"


def mask(category: Category, value: str) -> str:
    """Return a display-safe rendering of *value* — the real value never leaves detection.

    Rule-specific shapes:
      * e-mail     -> "s•••@e•••.tn"  (first char + bullets for local and SLD, keep TLD)
      * phone      -> keep the last two digits, bullet the rest (separators preserved)
      * keyword    -> shown as-is
    Any unexpected category falls back to hiding everything by the last four characters.
    """
    if category is Category.SECRET:
        return "\u2022" * 8
    if category is Category.EMAIL:
        return _mask_email(value)
    if category is Category.PHONE:
        return _mask_phone(value)
    if category is Category.KEYWORD:
        return value
    # Conservative fallback: keep only the last four characters.
    if len(value) <= 4:
        return "••••"
    return "•••• •••• •••• " + value[-4:]


def _mask_email(value: str) -> str:
    local, _, domain = value.partition("@")
    masked_local = (local[0] if local else "") + _BULLET
    parts = domain.split(".")
    if len(parts) >= 2:
        head = parts[:-1]
        tld = parts[-1]
        masked_head = ".".join((p[0] if p else "") + _BULLET for p in head)
        masked_domain = f"{masked_head}.{tld}"
    else:
        masked_domain = (domain[0] if domain else "") + _BULLET
    return f"{masked_local}@{masked_domain}"


def _mask_phone(value: str) -> str:
    digit_indices = [i for i, ch in enumerate(value) if ch.isdigit()]
    keep = set(digit_indices[-2:]) if len(digit_indices) >= 2 else set()
    return "".join(ch if (not ch.isdigit() or i in keep) else "•" for i, ch in enumerate(value))


def value_hmac(key: bytes, rule_id: str, value: str) -> str:
    """HMAC-SHA256 hex of *rule_id* + normalised *value* (ADR-0006)."""
    norm = " ".join(value.strip().split()).lower()
    payload = f"{rule_id}\x00{norm}".encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


_CONTEXT_MARGIN = 30

# Safety net for values no rule detected (the bullet is excluded so masks are never re-masked).
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_DIGIT_RUN_RE = re.compile(r"(?<![\w\u2022])\+?\(?\d[\d\s().\-]{6,}\d(?![\w\u2022])")
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

_SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(?:password|passwd|pwd|api[_\- ]?key|token|secret)"
        r"\s*[:=]\s*(?:\"[^\"\n]+\"|'[^'\n]+'|\S+)"
    ),
    re.compile(r"\b(?:sk|pk|rk|ghp|xox[abp]|swt)[-_][A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)\b(?:secret|api)[_-](?:token|key)[_-][A-Za-z0-9_-]+"),
)


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

    for pattern in _SECRET_PATTERNS:
        raw.extend((match.start(), match.end(), Category.SECRET) for match in pattern.finditer(text))

    for match in _EMAIL_RE.finditer(text):
        raw.append((match.start(), match.end(), Category.EMAIL))

    for match in _DIGIT_RUN_RE.finditer(text):
        value = match.group()
        digits = sum(ch.isdigit() for ch in value)
        if 8 <= digits <= 19 and not _ISO_DATE_RE.fullmatch(value.strip()):
            raw.append((match.start(), match.end(), Category.PHONE))

    # Apply full redaction to repeated values that overlap a credential.
    secret_spans = [(start, end) for start, end, category in raw if category is Category.SECRET]

    protected_values = {
        text[start:end]
        for start, end, category in raw
        if category is not Category.SECRET
        and any(start < secret_end and end > secret_start for secret_start, secret_end in secret_spans)
    }

    for value in protected_values:
        if not value:
            continue
        position = text.find(value)
        while position != -1:
            raw.append((position, position + len(value), Category.SECRET))
            position = text.find(value, position + len(value))

    raw.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    merged: list[tuple[int, int, Category]] = []
    for start, end, category in raw:
        if merged and start < merged[-1][1]:  # overlaps the previous range: extend it
            previous_start, previous_end, previous_category = merged[-1]
            if previous_category == category:
                chosen = category
            elif previous_category is Category.KEYWORD:
                chosen = category
            elif category is Category.KEYWORD:
                chosen = previous_category
            else:
                chosen = Category.SECRET
            merged[-1] = (previous_start, max(previous_end, end), chosen)
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
    return window
