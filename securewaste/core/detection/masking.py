"""Masking and keyed hashing (FR-13, ADR-0006). Owner: Milestone 1 issue #5.

mask(category, value)        -> "•••• •••• •••• 4242", "s•••@e•••.tn", "AKIA••••••••"
value_hmac(key, rule_id, v)  -> HMAC-SHA256 hex of rule_id + normalised value (use hmac + hashlib)
"""

from __future__ import annotations

import hashlib
import hmac
import re

from securewaste.core.detection.catalogue import Category


def mask(category: Category, value: str) -> str:
    """Return a masked version of the value appropriate for its category.

    Masking patterns:
    - EMAIL: s•••@e•••.tn (first char of local, first char of domain, mask rest)
    - PHONE: +44 •••• •••••• (keep country code, mask rest, preserve formatting)
    - PAYMENT_CARD: •••• •••• •••• 4242 (show last 4)
    - IBAN: •••• •••• •••• •••• •••• 12 (show last 2 groups)
    - SECRET: AKIA•••••••• (show prefix, mask rest)
    - NATIONAL_ID, PASSPORT: •••••••• (fully masked)
    - CONFIDENTIALITY_LABEL, KEYWORD: shown as-is (not sensitive values)
    """
    if category == Category.EMAIL:
        return _mask_email(value)
    elif category == Category.PHONE:
        return _mask_phone(value)
    elif category == Category.PAYMENT_CARD:
        return _mask_payment_card(value)
    elif category == Category.IBAN:
        return _mask_iban(value)
    elif category == Category.SECRET:
        return _mask_secret(value)
    elif category in (Category.NATIONAL_ID, Category.PASSPORT):
        return "•" * min(len(value), 20)
    elif category in (Category.CONFIDENTIALITY_LABEL, Category.KEYWORD):
        return value  # Keywords/labels are not sensitive values
    else:
        return "•" * min(len(value), 20)


def _mask_email(value: str) -> str:
    """Mask email: j••••@e•••••.com"""
    if "@" not in value:
        return "•" * len(value)

    local, domain = value.split("@", 1)
    # Mask local part: keep first char
    masked_local = local[0] + "•" * (len(local) - 1) if local else "•"

    # Mask domain: keep first char of each label, mask rest
    domain_parts = domain.split(".")
    masked_domain_parts = []
    for part in domain_parts:
        if part:
            masked_domain_parts.append(part[0] + "•" * (len(part) - 1))
        else:
            masked_domain_parts.append("•")

    return f"{masked_local}@{'•'.join(masked_domain_parts)}"


def _mask_phone(value: str) -> str:
    """Mask phone: keep country code, mask rest."""
    # Extract digits
    digits = re.sub(r"\D", "", value)

    if value.startswith("+"):
        # International: keep + and country code (1-3 digits after +)
        # Country code is 1-3 digits
        if len(digits) >= 2:
            country_code_len = 1
            if len(digits) >= 3 and digits[1] in "123456789":
                country_code_len = 2
            if len(digits) >= 4 and digits[1:3] in ("20", "27", "30", "31", "32", "33", "34", "36", "39", "40", "41", "43", "44", "45", "46", "47", "48", "49", "51", "52", "53", "54", "55", "56", "57", "58", "60", "61", "62", "63", "64", "65", "66", "81", "82", "84", "86", "90", "91", "92", "93", "94", "95", "98", "99"):
                country_code_len = 2

            country_code = digits[:1 + country_code_len]
            masked_rest = "•" * (len(digits) - len(country_code))
            # Try to preserve some formatting
            return f"+{country_code[1:]} {_group_masked(masked_rest)}"
    # National format: mask all but last 4
    if len(digits) >= 4:
        masked = "•" * (len(digits) - 4) + digits[-4:]
        return _group_masked(masked)
    return "•" * len(digits)


def _group_masked(masked_digits: str) -> str:
    """Group masked digits with spaces for readability."""
    # Group in 3-4 digit chunks
    parts = []
    for i in range(0, len(masked_digits), 4):
        parts.append(masked_digits[i:i+4])
    return " ".join(parts)


def _mask_payment_card(value: str) -> str:
    """Mask payment card: show last 4 digits."""
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 4:
        return "•••• •••• •••• " + digits[-4:]
    return "•" * len(digits)


def _mask_iban(value: str) -> str:
    """Mask IBAN: show last 2 groups (4 chars)."""
    # IBAN format: CC KK BBBB BBBB BBBB BBBB (spaces for readability)
    cleaned = re.sub(r"\s+", "", value.upper())
    if len(cleaned) >= 4:
        # Show last 4 chars
        masked = "•" * (len(cleaned) - 4) + cleaned[-4:]
        # Group in 4s
        parts = [masked[i:i+4] for i in range(0, len(masked), 4)]
        return " ".join(parts)
    return "•" * len(cleaned)


def _mask_secret(value: str) -> str:
    """Mask secret/API key: show prefix (first 4), mask rest."""
    if len(value) <= 8:
        return "•" * len(value)
    return value[:4] + "•" * (len(value) - 4)


def value_hmac(key: bytes, rule_id: str, value: str) -> str:
    """Compute HMAC-SHA256 of rule_id + normalized value.

    The HMAC is used to:
    1. Deduplicate findings (same value, same rule, same page)
    2. Locate values for redaction without storing raw values

    Normalization:
    - For emails: lowercase
    - For cards/IBANs: digits only
    - For others: stripped whitespace, lowercase
    """
    normalized = _normalize_for_hmac(rule_id, value)
    data = f"{rule_id}:{normalized}".encode("utf-8")
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def _normalize_for_hmac(rule_id: str, value: str) -> str:
    """Normalize value for consistent HMAC across detections."""
    rule_lower = rule_id.lower()

    if "email" in rule_lower:
        return value.lower().strip()
    elif "payment_card" in rule_lower or "card" in rule_lower:
        return re.sub(r"\D", "", value)
    elif "iban" in rule_lower:
        return re.sub(r"\s+", "", value.upper())
    elif "phone" in rule_lower:
        return re.sub(r"\D", "", value)
    elif "secret" in rule_lower or "key" in rule_lower:
        return value.strip()
    else:
        return value.strip().lower()
