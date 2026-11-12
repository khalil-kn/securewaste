"""Masking and keyed hashing (FR-13, ADR-0006). Owner: Milestone 1 issue #5.

mask(category, value)        -> "•••• •••• •••• 4242", "s•••@e•••.tn", "AKIA••••••••"
value_hmac(key, rule_id, v)  -> HMAC-SHA256 hex of rule_id + normalised value (use hmac + hashlib)
"""

from __future__ import annotations

import hashlib
import hmac

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
