"""
securewaste/core/privacy.py

One place that guarantees sensitive data is never shown or logged:

  * mask_value()            - masks a single value by type
  * build_masked_context()  - context snippet with EVERY sensitive value masked
                              (not only the current finding's), cut on word
                              boundaries so no half-words like "CONFIDENTI"
  * scrub()                 - safety-net regex scrubber for any string
  * install_log_redaction() - scrubs every log record (messages + tracebacks)

A "finding" can be an object or a dict with: start, end, and type/kind/category.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Iterable

DOT = "\u2022"  # •

# Words that must never be shown (extend as needed). Matches e.g. CONFIDENTIAL,
# SECRET_TOKEN_998877, "internal use only", case-insensitive.
SENSITIVE_KEYWORDS = (
    "confidential", "strictly confidential", "top secret", "secret",
    "internal use only", "restricted", "classified",
)

_KW = "|".join(sorted((re.escape(k).replace(r"\ ", r"\s+") for k in SENSITIVE_KEYWORDS),
                      key=len, reverse=True))

# (kind, regex) - order matters for overlaps (earlier wins).
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("secret", re.compile(r"(?i)\b(?:password|passwd|pwd|api[_\- ]?key|token|secret)\s*[:=]\s*\S+")),
    ("secret", re.compile(r"\b(?:sk|pk|rk|ghp|xox[abp])[-_][A-Za-z0-9_\-]{8,}")),
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")),
    ("card", re.compile(r"(?<![\d])(?:\d[ \-]?){13,19}(?![\d])")),
    ("phone", re.compile(r"(?<![\w])\+?\(?\d[\d\s().\-]{6,}\d(?![\w])")),
    ("keyword", re.compile(rf"(?i)(?<![A-Za-z0-9])(?:{_KW})(?:[_\-][A-Za-z0-9]+)*(?![A-Za-z0-9])")),
]


# ----------------------------------------------------------------- masking --
def mask_value(value: str, kind: str = "") -> str:
    kind = (kind or "").lower()
    if not value:
        return value
    if "mail" in kind or ("@" in value and "." in value):
        local, _, domain = value.partition("@")
        host, _, tld = domain.rpartition(".")
        return f"{local[:1]}{DOT*3}@{host[:1]}{DOT*3}.{tld}"
    if kind in ("phone", "card", "iban", "ssn", "id", "national_id"):
        digits = [i for i, c in enumerate(value) if c.isdigit()]
        keep = set(digits[-2:])
        return "".join(c if (not c.isdigit() or i in keep) else DOT
                       for i, c in enumerate(value))
    # secrets, keywords, anything else: fixed length so length is not leaked
    return DOT * 8


# ------------------------------------------------------------ span helpers --
def _get(f: Any, *names: str, default=None):
    for n in names:
        v = f.get(n) if isinstance(f, dict) else getattr(f, n, None)
        if v is not None:
            return v
    return default


def _spans(text: str, findings: Iterable[Any] = ()) -> list[tuple[int, int, str]]:
    """Your findings + safety-net regexes, overlaps merged."""
    raw: list[tuple[int, int, str]] = []
    for f in findings or ():
        s, e = _get(f, "start"), _get(f, "end")
        if isinstance(s, int) and isinstance(e, int) and 0 <= s < e <= len(text):
            raw.append((s, e, str(_get(f, "type", "kind", "category", default=""))))
    for kind, rx in _PATTERNS:
        raw += [(m.start(), m.end(), kind) for m in rx.finditer(text)
                if not (kind == "phone" and not 8 <= sum(c.isdigit() for c in m.group()) <= 15)
                and not (kind == "card" and not 13 <= sum(c.isdigit() for c in m.group()) <= 19)]
    raw.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    merged: list[list] = []
    for s, e, k in raw:
        if merged and s < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e, k])
    return [(s, e, k) for s, e, k in merged]


def mask_text(text: str, findings: Iterable[Any] = ()):
    """Return (masked_text, mapping) where mapping = [(o_start, o_end, m_start, m_end)]."""
    out, mapping, pos, cur = [], [], 0, 0
    for s, e, k in _spans(text, findings):
        out.append(text[pos:s]); cur += s - pos
        m = mask_value(text[s:e], k)
        out.append(m); mapping.append((s, e, cur, cur + len(m)))
        cur += len(m); pos = e
    out.append(text[pos:])
    return "".join(out), mapping


def scrub(text: str) -> str:
    """Safety net: mask anything that looks sensitive in an arbitrary string."""
    return mask_text(text or "")[0]


# ----------------------------------------------------------------- context --
def build_masked_context(text: str, findings: Iterable[Any], target: Any = None,
                         window: int = 60) -> str:
    """
    Context around `target` (one of `findings`), with ALL sensitive values masked.
    Masking happens on the full text BEFORE slicing, so nothing is cut in half.
    """
    masked, mapping = mask_text(text, findings)
    c_start, c_end = 0, 0
    if target is not None:
        ts = _get(target, "start")
        for o_s, o_e, m_s, m_e in mapping:
            if isinstance(ts, int) and o_s <= ts < o_e:
                c_start, c_end = m_s, m_e
                break
    lo, hi = max(0, c_start - window), min(len(masked), c_end + window)

    # snap to word boundaries (never show half a word)
    if lo > 0 and not masked[lo - 1].isspace():
        nxt = re.search(r"\s", masked[lo:])
        lo = lo + nxt.end() if nxt else lo
    if hi < len(masked) and not masked[hi].isspace():
        prev = masked.rfind(" ", c_end, hi)
        prev2 = masked.rfind("\n", c_end, hi)
        cut = max(prev, prev2)
        hi = cut if cut != -1 else hi

    snippet = re.sub(r"\s+", " ", masked[lo:hi]).strip()
    snippet = scrub(snippet)  # defence in depth
    return ("\u2026 " if lo > 0 else "") + snippet + (" \u2026" if hi < len(masked) else "")


# ----------------------------------------------------------------- logging --
_installed = False


def install_log_redaction() -> None:
    """Scrub every LogRecord at creation, so ALL handlers (incl. pytest caplog) are safe."""
    global _installed
    if _installed:
        return
    old_factory = logging.getLogRecordFactory()

    def factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        try:
            record.msg = scrub(record.getMessage())
            record.args = ()
            if record.exc_info and not record.exc_text:
                record.exc_text = scrub(logging.Formatter().formatException(record.exc_info))
        except Exception:  # never break logging
            record.msg, record.args = "[log message withheld]", ()
        return record

    logging.setLogRecordFactory(factory)
    _installed = True